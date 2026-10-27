//! AST adjustments for actual Babel preset 7.22.5 defaults, not tsc defaults.
use oxc_allocator::Allocator;
use oxc_ast::{ast::*, AstBuilder, AstKind};
use oxc_ast_visit::{walk_mut, VisitMut};
use oxc_span::{Span, SPAN};
use oxc_syntax::{
    number::{NumberBase, ToJsString},
    operator::{BinaryOperator, UnaryOperator},
};
use std::collections::{HashMap, HashSet};
const MARKER: Span = Span::new(u32::MAX - 1, u32::MAX - 1);

pub struct Before<'a> {
    ast: AstBuilder<'a>,
    facts: Facts,
    pub invalid: bool,
    pub using: HashMap<u32, VariableDeclarationKind>,
    pub namespace_module_marker: bool,
    pub erased_comment_ranges: Vec<Span>,
    pub namespace_aliases: Vec<String>,
    pub impure_enums: Vec<u32>,
    pub adjacent_type_comments: Vec<Span>,
    pub lowered_declarations: Vec<u32>,
    pub namespace_locations: Vec<(String, Span)>,
    namespace_depth: usize,
    ambient_class: bool,
}
impl<'a> Before<'a> {
    pub fn new(allocator: &'a Allocator, facts: Facts) -> Self {
        Self {
            ast: AstBuilder::new(allocator),
            facts,
            invalid: false,
            using: HashMap::new(),
            namespace_module_marker: false,
            erased_comment_ranges: Vec::new(),
            namespace_aliases: Vec::new(),
            impure_enums: Vec::new(),
            adjacent_type_comments: Vec::new(),
            lowered_declarations: Vec::new(),
            namespace_locations: Vec::new(),
            namespace_depth: 0,
            ambient_class: false,
        }
    }
}
impl<'a> VisitMut<'a> for Before<'a> {
    fn visit_ts_type_annotation(&mut self, annotation: &mut TSTypeAnnotation<'a>) {
        self.erased_comment_ranges.push(annotation.span);
        self.adjacent_type_comments.push(annotation.span);
    }
    fn visit_ts_enum_declaration(&mut self, declaration: &mut TSEnumDeclaration<'a>) {
        self.erased_comment_ranges.push(declaration.span);
        self.lowered_declarations.push(declaration.span.start);
        let mut known = HashMap::new();
        let mut prior: Option<Constant> = Some(Constant::Number(-1.0));
        for member in &mut declaration.members {
            let member_name = match &member.id {
                TSEnumMemberName::Identifier(id) => id.name.to_string(),
                TSEnumMemberName::String(s) => s.value.to_string(),
            };
            if let Some(expression) = &mut member.initializer {
                let mut evaluated_nonfinite = HashSet::new();
                prior = evaluate(
                    expression,
                    &mut |id| {
                        if matches!(id.name.as_str(), "NaN" | "Infinity")
                            && !self.facts.bound.contains(&id.span.start)
                        {
                            evaluated_nonfinite.insert(id.span.start);
                        }
                        self.facts.literals.get(&id.span.start).cloned()
                    },
                    &known,
                    &mut 8192,
                );
                if let Some(value) = &prior {
                    *expression = value.expression(self.ast);
                } else if rewrite_nonfinite(
                    expression,
                    declaration.id.name,
                    &evaluated_nonfinite,
                    self.ast,
                ) {
                    self.impure_enums.push(declaration.span.start);
                }
            } else {
                if matches!(prior, Some(Constant::String(_))) {
                    self.invalid = true;
                }
                prior = match prior {
                    Some(Constant::Number(n)) => Some(Constant::Number(n + 1.0)),
                    _ => None,
                };
            }
            if let Some(value) = prior.clone() {
                known.insert(member_name, value);
            }
        }
        walk_mut::walk_ts_enum_declaration(self, declaration);
    }
    fn visit_statements(&mut self, statements: &mut oxc_allocator::Vec<'a, Statement<'a>>) {
        for statement in statements.iter_mut() {
            if let Statement::ExportDefaultDeclaration(export) = statement {
                if matches!(&export.declaration, ExportDefaultDeclarationKind::Identifier(id) if self.facts.type_references.contains(&id.span.start))
                {
                    *statement =
                        Statement::from(self.ast.module_declaration_export_named_declaration(
                            SPAN,
                            None,
                            self.ast.vec(),
                            None,
                            ImportOrExportKind::Value,
                            None::<oxc_allocator::Box<WithClause>>,
                        ));
                }
            }
        }
        walk_mut::walk_statements(self, statements);
    }
    fn visit_ts_type_alias_declaration(&mut self, declaration: &mut TSTypeAliasDeclaration<'a>) {
        self.erased_comment_ranges.push(declaration.span);
        walk_mut::walk_ts_type_alias_declaration(self, declaration);
    }
    fn visit_ts_interface_declaration(&mut self, declaration: &mut TSInterfaceDeclaration<'a>) {
        self.erased_comment_ranges.push(declaration.span);
        walk_mut::walk_ts_interface_declaration(self, declaration);
    }
    fn visit_import_declaration(&mut self, declaration: &mut ImportDeclaration<'a>) {
        if declaration.phase.is_some()
            || declaration
                .with_clause
                .as_ref()
                .is_some_and(|c| c.attributes_keyword.name == "assert")
        {
            self.invalid = true;
        }
        walk_mut::walk_import_declaration(self, declaration);
    }
    fn visit_accessor_property(&mut self, _: &mut AccessorProperty<'a>) {
        self.invalid = true;
    }
    fn visit_formal_parameter(&mut self, parameter: &mut FormalParameter<'a>) {
        if (parameter.accessibility.is_some() || parameter.readonly || parameter.r#override)
            && !matches!(
                parameter.pattern.kind,
                BindingPatternKind::BindingIdentifier(_) | BindingPatternKind::AssignmentPattern(_)
            )
        {
            self.invalid = true;
        }
        if parameter.accessibility.is_some() || parameter.readonly || parameter.r#override {
            if let BindingPatternKind::AssignmentPattern(assignment) = &parameter.pattern.kind {
                if !matches!(
                    assignment.left.kind,
                    BindingPatternKind::BindingIdentifier(_)
                ) {
                    self.invalid = true;
                }
            }
        }
        walk_mut::walk_formal_parameter(self, parameter);
    }
    fn visit_decorator(&mut self, _: &mut Decorator<'a>) {
        self.invalid = true;
    }
    fn visit_ts_import_equals_declaration(
        &mut self,
        declaration: &mut TSImportEqualsDeclaration<'a>,
    ) {
        if matches!(
            declaration.module_reference,
            TSModuleReference::ExternalModuleReference(_)
        ) {
            self.invalid = true;
        }
    }
    fn visit_ts_export_assignment(&mut self, _: &mut TSExportAssignment<'a>) {
        self.invalid = true;
    }
    fn visit_class(&mut self, class: &mut Class<'a>) {
        let ambient = self.ambient_class;
        self.ambient_class |= class.declare;
        walk_mut::walk_class(self, class);
        self.ambient_class = ambient;
    }
    fn visit_class_body(&mut self, body: &mut ClassBody<'a>) {
        for element in &mut body.body {
            if let ClassElement::PropertyDefinition(field) = element {
                if (field.declare && !self.ambient_class)
                    || (field.definite && field.value.is_some())
                {
                    self.invalid = true;
                }
                // Babel 7 default allowDeclareFields=false erases uninitialized
                // public/protected/TS-private fields but retains JS #private fields.
                if field.value.is_none() && !matches!(field.key, PropertyKey::PrivateIdentifier(_))
                {
                    field.declare = true;
                }
            }
        }
        walk_mut::walk_class_body(self, body);
    }
    fn visit_variable_declaration(&mut self, decl: &mut VariableDeclaration<'a>) {
        if matches!(
            decl.kind,
            VariableDeclarationKind::Using | VariableDeclarationKind::AwaitUsing
        ) {
            self.using.insert(decl.span.start, decl.kind);
            decl.kind = VariableDeclarationKind::Const;
            for d in &mut decl.declarations {
                d.kind = VariableDeclarationKind::Const;
            }
        }
        walk_mut::walk_variable_declaration(self, decl);
    }
    fn visit_ts_module_declaration(&mut self, decl: &mut TSModuleDeclaration<'a>) {
        if decl.declare || matches!(decl.id, TSModuleDeclarationName::StringLiteral(_)) {
            return;
        }
        self.lowered_declarations.push(decl.span.start);
        if let TSModuleDeclarationName::Identifier(id) = &decl.id {
            self.namespace_locations
                .push((id.name.to_string(), decl.span));
        }
        self.namespace_depth += 1;
        walk_mut::walk_ts_module_declaration(self, decl);
        self.namespace_depth -= 1;
    }
    fn visit_ts_module_block(&mut self, block: &mut TSModuleBlock<'a>) {
        if block.body.iter().all(|statement| match statement {
            Statement::TSTypeAliasDeclaration(_) | Statement::TSInterfaceDeclaration(_) => true,
            Statement::ExportNamedDeclaration(export) => matches!(
                export.declaration,
                Some(
                    Declaration::TSTypeAliasDeclaration(_) | Declaration::TSInterfaceDeclaration(_)
                )
            ),
            _ => false,
        }) {
            self.erased_comment_ranges.push(block.span);
        }
        walk_mut::walk_ts_module_block(self, block);
        // A synthetic empty statement retains Babel's empty namespace IIFE.
        // Remove it after native namespace lowering, before printing.
        block.body.push(self.ast.statement_empty(MARKER));
    }
    fn visit_export_named_declaration(&mut self, decl: &mut ExportNamedDeclaration<'a>) {
        if self.namespace_depth > 0 {
            if let Some(Declaration::TSImportEqualsDeclaration(alias)) = &decl.declaration {
                self.namespace_aliases.push(alias.id.name.to_string());
            }
        }
        if self.namespace_depth > 0
            && (decl.export_kind == ImportOrExportKind::Type
                || matches!(
                    decl.declaration,
                    Some(
                        Declaration::TSTypeAliasDeclaration(_)
                            | Declaration::TSInterfaceDeclaration(_)
                    )
                ))
        {
            self.namespace_module_marker = true;
        }
        walk_mut::walk_export_named_declaration(self, decl);
    }
}
pub struct After {
    pub namespace_locations: Vec<(String, Span)>,
    pub using: HashMap<u32, VariableDeclarationKind>,
    pub namespace_aliases: Vec<String>,
    pub impure_enums: Vec<u32>,
}
impl<'a> VisitMut<'a> for After {
    fn visit_call_expression(&mut self, call: &mut CallExpression<'a>) {
        if let Expression::FunctionExpression(function) = &call.callee {
            if self
                .impure_enums
                .contains(&function.body.as_ref().map_or(0, |b| b.span.start))
            {
                call.pure = false;
            }
        }
        walk_mut::walk_call_expression(self, call);
    }

    fn visit_statements(&mut self, statements: &mut oxc_allocator::Vec<'a, Statement<'a>>) {
        statements.retain(|s| {
            if matches!(s, Statement::EmptyStatement(e) if e.span == MARKER) {
                return false;
            }
            if let Statement::ExpressionStatement(e) = s {
                if e.span == SPAN {
                    if let Expression::AssignmentExpression(a) = &e.expression {
                        if let (
                            AssignmentTarget::StaticMemberExpression(member),
                            Expression::Identifier(identifier),
                        ) = (&a.left, &a.right)
                        {
                            if member.property.name == identifier.name
                                && self
                                    .namespace_aliases
                                    .iter()
                                    .any(|s| s == identifier.name.as_str())
                            {
                                return false;
                            }
                        }
                    }
                }
            }
            true
        });
        walk_mut::walk_statements(self, statements);
    }
    fn visit_variable_declaration(&mut self, decl: &mut VariableDeclaration<'a>) {
        if decl.span == SPAN && decl.kind == VariableDeclarationKind::Let {
            if let Some(d) = decl.declarations.first() {
                if let BindingPatternKind::BindingIdentifier(id) = &d.id.kind {
                    if d.init.is_none() {
                        if let Some((_, span)) = self
                            .namespace_locations
                            .iter()
                            .find(|(name, _)| name == id.name.as_str())
                        {
                            decl.span = Span::new(span.start, span.start + 1);
                        }
                    }
                }
            }
        }
        if let Some(kind) = self.using.get(&decl.span.start) {
            decl.kind = *kind;
            for d in &mut decl.declarations {
                d.kind = *kind;
            }
        }
        walk_mut::walk_variable_declaration(self, decl);
    }
}

fn rewrite_nonfinite<'a>(
    expression: &mut Expression<'a>,
    name: oxc_span::Atom<'a>,
    evaluated: &HashSet<u32>,
    ast: AstBuilder<'a>,
) -> bool {
    match expression {
        Expression::Identifier(identifier)
            if matches!(identifier.name.as_str(), "NaN" | "Infinity")
                && evaluated.contains(&identifier.span.start) =>
        {
            let property = ast.identifier_name(SPAN, identifier.name);
            *expression = Expression::from(ast.member_expression_static(
                SPAN,
                ast.expression_identifier(SPAN, name),
                property,
                false,
            ));
            true
        }
        Expression::UnaryExpression(unary) => {
            rewrite_nonfinite(&mut unary.argument, name, evaluated, ast)
        }
        Expression::BinaryExpression(binary) => {
            let left = rewrite_nonfinite(&mut binary.left, name, evaluated, ast);
            let right = rewrite_nonfinite(&mut binary.right, name, evaluated, ast);
            left || right
        }
        Expression::ParenthesizedExpression(p) => {
            rewrite_nonfinite(&mut p.expression, name, evaluated, ast)
        }
        Expression::TemplateLiteral(t) => {
            let mut changed = false;
            for e in &mut t.expressions {
                changed |= rewrite_nonfinite(e, name, evaluated, ast);
            }
            changed
        }
        _ => false,
    }
}

// Babel evaluates stable primitive bindings while lowering enums. These facts
// come from Rust lexical binding resolution, never a JS evaluator or name-only map.
#[derive(Clone)]
enum Constant {
    Number(f64),
    String(String),
}
#[derive(Default)]
pub struct Facts {
    literals: HashMap<u32, Constant>,
    bound: HashSet<u32>,
    type_references: HashSet<u32>,
}
impl Facts {
    pub fn from_program(program: &Program<'_>) -> Self {
        let built = oxc_semantic::SemanticBuilder::new().build(program);
        let semantic = &built.semantic;
        let scoping = semantic.scoping();
        let mut facts = Self::default();
        for node in semantic.nodes().iter() {
            let AstKind::IdentifierReference(id) = node.kind() else {
                continue;
            };
            let Some(reference) = id.reference_id.get() else {
                continue;
            };
            let Some(symbol) = scoping.get_reference(reference).symbol_id() else {
                continue;
            };
            let flags = scoping.symbol_flags(symbol);
            if flags.is_type() && !flags.is_value() {
                facts.type_references.insert(id.span.start);
            }
            facts.bound.insert(id.span.start);
            let mut resolver = BindingEvaluator {
                semantic,
                active: HashSet::new(),
                remaining: 8192,
            };
            if let Some(value) = resolver.reference(id) {
                facts.literals.insert(id.span.start, value);
            }
        }
        facts
    }
}

// Resolve declarations by semantic symbol identity, including forward aliases.
// A cycle set and shared work counter bound recursive binding/expression work.
struct BindingEvaluator<'s, 'a> {
    semantic: &'s oxc_semantic::Semantic<'a>,
    active: HashSet<oxc_semantic::SymbolId>,
    remaining: usize,
}
impl BindingEvaluator<'_, '_> {
    fn reference(&mut self, id: &IdentifierReference<'_>) -> Option<Constant> {
        self.remaining = self.remaining.checked_sub(1)?;
        let scoping = self.semantic.scoping();
        let symbol = scoping.get_reference(id.reference_id.get()?).symbol_id()?;
        if self.active.len() >= 128
            || scoping.symbol_is_mutated(symbol)
            || !self.active.insert(symbol)
        {
            return None;
        }
        let node = self
            .semantic
            .nodes()
            .kind(scoping.symbol_declaration(symbol));
        let variable = match node {
            AstKind::VariableDeclarator(d) => Some(d),
            AstKind::VariableDeclaration(d) => d.declarations.iter().find(|d| matches!(&d.id.kind, BindingPatternKind::BindingIdentifier(b) if b.symbol_id.get() == Some(symbol))),
            _ => None,
        };
        let result = variable.and_then(|d| d.init.as_ref()).and_then(|expr| {
            let mut work = self.remaining;
            let value = evaluate(
                expr,
                &mut |id| self.reference(id),
                &HashMap::new(),
                &mut work,
            );
            self.remaining = self.remaining.min(work);
            value
        });
        self.active.remove(&symbol);
        result
    }
}
impl Constant {
    fn expression<'a>(&self, ast: AstBuilder<'a>) -> Expression<'a> {
        match self {
            Self::Number(n) => ast.expression_numeric_literal(SPAN, *n, None, NumberBase::Decimal),
            Self::String(s) => ast.expression_string_literal(SPAN, ast.atom(s), None),
        }
    }
    fn string(&self) -> String {
        match self {
            Self::Number(n) => n.to_js_string(),
            Self::String(s) => s.clone(),
        }
    }
    fn number(&self) -> f64 {
        match self {
            Self::Number(n) => *n,
            Self::String(s) => {
                let s = s.trim_matches(|c: char| matches!(c, '\u{0009}'..='\u{000d}' | '\u{0020}' | '\u{00a0}' | '\u{1680}' | '\u{2000}'..='\u{200a}' | '\u{2028}' | '\u{2029}' | '\u{202f}' | '\u{205f}' | '\u{3000}' | '\u{feff}'));
                if s.is_empty() {
                    return 0.0;
                }
                for (prefix, radix) in [
                    ("0x", 16),
                    ("0X", 16),
                    ("0b", 2),
                    ("0B", 2),
                    ("0o", 8),
                    ("0O", 8),
                ] {
                    if let Some(digits) = s.strip_prefix(prefix) {
                        if digits.is_empty() {
                            return f64::NAN;
                        }
                        return digits
                            .chars()
                            .try_fold(0.0, |n, c| {
                                c.to_digit(radix)
                                    .map(|v| n * f64::from(radix) + f64::from(v))
                            })
                            .unwrap_or(f64::NAN);
                    }
                }
                if matches!(s, "Infinity" | "+Infinity") {
                    f64::INFINITY
                } else if s == "-Infinity" {
                    f64::NEG_INFINITY
                } else if s.contains("inf") || s.contains("Inf") {
                    f64::NAN
                } else {
                    s.parse().unwrap_or(f64::NAN)
                }
            }
        }
    }
}
fn int32(n: f64) -> i32 {
    if !n.is_finite() || n == 0.0 {
        return 0;
    }
    let u = n.trunc().rem_euclid(4294967296.0) as u32;
    u as i32
}
// This deliberately mirrors the locked Babel enum evaluator, including unary
// plus preserving a string and template interpolation accepting references only.
fn evaluate(
    expression: &Expression<'_>,
    reference: &mut dyn FnMut(&IdentifierReference<'_>) -> Option<Constant>,
    members: &HashMap<String, Constant>,
    work: &mut usize,
) -> Option<Constant> {
    *work = work.checked_sub(1)?;
    let value = match expression {
        Expression::NumericLiteral(n) => Constant::Number(n.value),
        Expression::StringLiteral(s) => Constant::String(s.value.to_string()),
        Expression::Identifier(id) => {
            return members
                .get(id.name.as_str())
                .cloned()
                .or_else(|| reference(id))
        }
        Expression::ParenthesizedExpression(p) => {
            return evaluate(&p.expression, reference, members, work)
        }
        Expression::TemplateLiteral(t) => {
            let mut result = String::new();
            for (i, q) in t.quasis.iter().enumerate() {
                result.push_str(q.value.cooked.as_ref()?.as_str());
                if let Some(expr) = t.expressions.get(i) {
                    // Actual Babel uses evaluateRef here, not evaluate.
                    if !matches!(expr, Expression::Identifier(_)) {
                        return None;
                    }
                    result.push_str(&evaluate(expr, reference, members, work)?.string());
                }
            }
            Constant::String(result)
        }
        Expression::UnaryExpression(u) => {
            let v = evaluate(&u.argument, reference, members, work)?;
            match u.operator {
                UnaryOperator::UnaryPlus => v,
                UnaryOperator::UnaryNegation => Constant::Number(-v.number()),
                UnaryOperator::BitwiseNot => Constant::Number(f64::from(!int32(v.number()))),
                _ => return None,
            }
        }
        Expression::BinaryExpression(b) => {
            let l = evaluate(&b.left, reference, members, work)?;
            let r = evaluate(&b.right, reference, members, work)?;
            if b.operator == BinaryOperator::Addition
                && (matches!(l, Constant::String(_)) || matches!(r, Constant::String(_)))
            {
                Constant::String(l.string() + &r.string())
            } else {
                let (l, r) = (l.number(), r.number());
                Constant::Number(match b.operator {
                    BinaryOperator::Addition => l + r,
                    BinaryOperator::Subtraction => l - r,
                    BinaryOperator::Multiplication => l * r,
                    BinaryOperator::Division => l / r,
                    BinaryOperator::Remainder => l % r,
                    BinaryOperator::Exponential => l.powf(r),
                    BinaryOperator::BitwiseOR => f64::from(int32(l) | int32(r)),
                    BinaryOperator::BitwiseAnd => f64::from(int32(l) & int32(r)),
                    BinaryOperator::BitwiseXOR => f64::from(int32(l) ^ int32(r)),
                    BinaryOperator::ShiftLeft => f64::from(int32(l).wrapping_shl(int32(r) as u32)),
                    BinaryOperator::ShiftRight => f64::from(int32(l).wrapping_shr(int32(r) as u32)),
                    BinaryOperator::ShiftRightZeroFill => {
                        f64::from((int32(l) as u32).wrapping_shr(int32(r) as u32))
                    }
                    _ => return None,
                })
            }
        }
        _ => return None,
    };
    // Match the output bound without permitting exponential alias/template growth.
    if matches!(&value,Constant::String(s) if s.len() > crate::compiler::MAX_OUTPUT) {
        return None;
    }
    Some(value)
}
