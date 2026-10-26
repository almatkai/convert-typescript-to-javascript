//! Native parse/transform/codegen. Never evaluates the supplied program.
use crate::compat::{After, Before, Facts};
use oxc_allocator::Allocator;
use oxc_ast::{ast::*, AstBuilder};
use oxc_ast_visit::VisitMut;
use oxc_codegen::CodeGenerator;
use oxc_parser::Parser;
use oxc_semantic::SemanticBuilder;
use oxc_span::SourceType;
use oxc_span::SPAN;
use oxc_transformer::{TransformOptions, Transformer};
use std::path::Path;

pub const MAX_INPUT: usize = 64 * 1024;
pub const MAX_OUTPUT: usize = 512 * 1024;
pub const FAILURE: &str = "Failed to transform TypeScript to JavaScript";

pub fn convert(source: &str) -> Result<String, &'static str> {
    // Third-party parser/transform invariant failures are conversion failures,
    // never process-wide success or partial output. No input is executed.
    std::panic::catch_unwind(|| convert_inner(source)).unwrap_or(Err(FAILURE))
}
fn convert_inner(source: &str) -> Result<String, &'static str> {
    if source.len() > MAX_INPUT {
        return Err("TypeScript input exceeds 64 KiB; nothing was delivered");
    }
    // Bound parser recursion conservatively before parsing. This scanner counts all
    // delimiters, including comments/strings, and therefore may overestimate depth.
    let mut depth = 0usize;
    let mut run = 0usize;
    for ch in source.chars() {
        run = if matches!(ch, ';' | '{' | '}' | '[' | ']' | ',') {
            0
        } else {
            run + 1
        };
        if run > 4096 {
            return Err(
                "TypeScript expression segment exceeds 4096 scalars; nothing was delivered",
            );
        }
        if matches!(ch, '(' | '{' | '[' | '<') {
            depth += 1;
            if depth > 128 {
                return Err(
                    "TypeScript structural complexity exceeds native limit; nothing was delivered",
                );
            }
        } else if matches!(ch, ')' | '}' | ']' | '>') {
            depth = depth.saturating_sub(1);
        }
    }
    let allocator = Allocator::default();
    let parsed = Parser::new(&allocator, source, SourceType::ts()).parse();
    if parsed.panicked || !parsed.errors.is_empty() {
        return Err(FAILURE);
    }
    let mut program = parsed.program;
    let originally_had_body = !program.body.is_empty();
    let facts = Facts::from_program(&program);
    let mut before = Before::new(&allocator, facts);
    before.visit_program(&mut program);
    if before.invalid {
        return Err(FAILURE);
    }
    let semantic = SemanticBuilder::new()
        .with_check_syntax_error(true)
        .with_scope_tree_child_ids(true)
        .build(&program);
    if semantic
        .errors
        .iter()
        .any(|e| e.message != "Enum member must have initializer.")
    {
        return Err(FAILURE);
    }
    let mut options = TransformOptions::default();
    options.typescript.allow_declare_fields = false;
    options.jsx.runtime = oxc_transformer::JsxRuntime::Classic;
    let transformed = Transformer::new(&allocator, Path::new("clipboard.ts"), &options)
        .build_with_scoping(semantic.semantic.into_scoping(), &mut program);
    if !transformed.errors.is_empty() {
        return Err(FAILURE);
    }
    After {
        namespace_locations: before.namespace_locations,
        using: before.using,
        namespace_aliases: before.namespace_aliases,
        impure_enums: before.impure_enums,
    }
    .visit_program(&mut program);
    if before.namespace_module_marker && !program.body.iter().any(|s| s.is_module_declaration()) {
        let ast = AstBuilder::new(&allocator);
        program.body.push(Statement::from(
            ast.module_declaration_export_named_declaration(
                SPAN,
                None,
                ast.vec(),
                None,
                ImportOrExportKind::Value,
                None::<oxc_allocator::Box<WithClause>>,
            ),
        ));
    }
    program.comments.retain(|c| {
        !before
            .erased_comment_ranges
            .iter()
            .any(|s| s.start <= c.span.start && s.end >= c.span.end)
            && !before.adjacent_type_comments.iter().any(|s| {
                s.end <= c.span.start
                    && source[s.end as usize..c.span.start as usize]
                        .trim()
                        .is_empty()
            })
    });
    if originally_had_body && program.body.is_empty() {
        program.comments.clear();
    }
    let code = CodeGenerator::new()
        .with_lowered_declarations(before.lowered_declarations)
        .build(&program)
        .code;
    let code = code.strip_suffix('\n').unwrap_or(&code).to_owned();
    if code.is_empty() {
        return Err(FAILURE);
    }
    if code.len() > MAX_OUTPUT {
        return Err("JavaScript output exceeds 512 KiB; nothing was delivered");
    }
    Ok(code)
}
