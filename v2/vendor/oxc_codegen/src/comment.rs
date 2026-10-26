// Native Babel-compatibility comment attachment over the surviving Rust AST.
// Original upstream implementation provenance is retained in UPSTREAM.json.
use crate::Codegen;
use oxc_ast::{
    AstKind, Comment,
    ast::{Argument, Program},
};
use oxc_ast_visit::Visit;
use oxc_span::{GetSpan, Span};
use rustc_hash::FxHashMap;

pub type CommentsMap = FxHashMap<u32, Vec<Comment>>;
#[derive(Default)]
struct Positions {
    spans: Vec<Span>,
    ends: std::collections::HashSet<u32>,
    bodies: Vec<Span>,
}
impl<'a> Visit<'a> for Positions {
    fn enter_node(&mut self, kind: AstKind<'a>) {
        let span = kind.span();
        if matches!(kind,AstKind::Function(f) if f.r#type == oxc_ast::ast::FunctionType::FunctionDeclaration)
        {
            self.ends.insert(span.end);
        }
        if matches!(
            kind,
            AstKind::PropertyDefinition(_)
                | AstKind::VariableDeclaration(_)
                | AstKind::ExpressionStatement(_)
                | AstKind::ReturnStatement(_)
                | AstKind::ThrowStatement(_)
                | AstKind::BreakStatement(_)
                | AstKind::ContinueStatement(_)
        ) {
            self.ends.insert(span.end);
        }
        if matches!(kind, AstKind::FunctionBody(_) | AstKind::BlockStatement(_)) {
            self.bodies.push(span);
        }
        if !matches!(kind, AstKind::Program(_)) && span.end > span.start {
            self.spans.push(span);
        }
    }
}
impl Codegen<'_> {
    pub(crate) fn build_comments(&mut self, program: &Program<'_>) {
        let mut positions = Positions::default();
        positions.visit_program(program);
        self.statement_ends = positions.ends;
        for original_comment in &program.comments {
            let mut normalized = *original_comment;
            let comment = &mut normalized;
            if comment.is_pure() || comment.is_no_side_effects() {
                continue;
            }
            let previous = positions
                .spans
                .iter()
                .filter(|s| s.end <= comment.span.start)
                .max_by_key(|s| s.end);
            let next = positions
                .spans
                .iter()
                .filter(|s| s.start >= comment.span.end)
                .min_by_key(|s| s.start);
            let previous_end = previous.map_or(0, |s| s.end);
            comment.preceded_by_newline = program.source_text
                [previous_end as usize..comment.span.start as usize]
                .contains('\n');
            comment.followed_by_newline = next.is_some_and(|s| {
                self.lowered_declarations.contains(&s.start)
                    || program.source_text[comment.span.end as usize..s.start as usize]
                        .contains('\n')
            });
            let trailing = previous.is_some_and(|s| {
                let gap = &program.source_text[s.end as usize..comment.span.start as usize];
                gap.chars().all(|c| matches!(c, ' ' | '\t' | '\r'))
            });
            if trailing {
                self.trailing_comments
                    .entry(previous.unwrap().end)
                    .or_default()
                    .push(*comment);
            } else {
                let body_end = positions
                    .bodies
                    .iter()
                    .filter(|s| {
                        s.start < comment.span.start
                            && s.end > comment.span.end
                            && next.is_none_or(|n| n.start >= s.end)
                    })
                    .min_by_key(|s| s.end - s.start)
                    .map(|s| s.end - 1);
                self.comments
                    .entry(body_end.unwrap_or_else(|| next.map_or(program.span.end, |s| s.start)))
                    .or_default()
                    .push(*comment);
            }
        }
    }
    pub(crate) fn has_comment(&self, start: u32) -> bool {
        self.comments.contains_key(&start)
    }
    pub(crate) fn contains_comment_in_call_like_expression(
        &self,
        span: Span,
        args: &[Argument<'_>],
    ) -> (bool, bool) {
        let end = self.print_comments && span.end > 0 && self.has_comment(span.end - 1);
        (
            end || self.print_comments && args.iter().any(|a| self.has_comment(a.span().start)),
            end,
        )
    }
    pub(crate) fn print_leading_comments(&mut self, start: u32) {
        if self.print_comments {
            if let Some(comments) = self.comments.remove(&start) {
                self.print_comments(&comments);
            }
        }
    }
    pub(crate) fn get_statement_comments(&mut self, start: u32) -> Option<Vec<Comment>> {
        self.comments.remove(&start)
    }
    pub(crate) fn print_statement_comments(&mut self, start: u32) {
        self.print_leading_comments(start);
    }
    pub(crate) fn print_expr_comments(&mut self, start: u32) -> bool {
        if !self.print_comments {
            return false;
        }
        if let Some(comments) = self.comments.remove(&start) {
            self.print_comments(&comments);
            true
        } else {
            false
        }
    }
    pub(crate) fn print_comments(&mut self, comments: &[Comment]) {
        for (index, comment) in comments.iter().enumerate() {
            if index > 0 && !comment.preceded_by_newline && !comments[index - 1].followed_by_newline
            {
                self.print_hard_space();
            }
            if comment.preceded_by_newline
                && !self.code.is_empty()
                && (0..self.code_len())
                    .filter_map(|i| self.code.peek_nth_byte_back(i))
                    .take_while(|c| *c != b'\n')
                    .any(|c| c != b' ' && c != b'\t')
            {
                self.print_hard_newline();
            }
            if self.last_byte() == Some(b'\n') {
                self.print_indent();
            }
            self.print_str(comment.span.source_text(self.source_text));
            if comment.is_line() || comment.followed_by_newline {
                self.print_hard_newline();
            }
        }
    }
    pub(crate) fn print_trailing_comments(&mut self, end: u32) {
        if !self.print_comments {
            return;
        }
        let Some(comments) = self.trailing_comments.remove(&end) else {
            return;
        };
        let code = std::mem::take(&mut self.code).into_string();
        let had_newline = code.ends_with('\n');
        self.code.print_str(code.trim_end_matches('\n'));
        for comment in &comments {
            self.print_hard_space();
            self.print_str(comment.span.source_text(self.source_text));
            if comment.is_line() {
                self.print_hard_newline();
            }
        }
        if had_newline && self.last_byte() != Some(b'\n') {
            self.print_hard_newline();
        }
    }
    pub(crate) fn flush_remaining_comments(&mut self) {
        let mut comments = self
            .comments
            .drain()
            .flat_map(|(_, v)| v)
            .collect::<Vec<_>>();
        comments.sort_by_key(|c| c.span.start);
        self.print_comments(&comments);
    }
    pub(crate) fn try_print_eof_legal_comments(&mut self) {}
}
