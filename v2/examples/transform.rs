//! QA-only stream transformer: no host, no effects, never executes input.
use std::io::{self, BufRead};
fn main() {
    for line in io::stdin().lock().lines() {
        let line = line.unwrap();
        let source: String = serde_json::from_str(&line).unwrap();
        let result = tezbar_convert_typescript_to_javascript::compiler::convert(&source);
        println!(
            "{}",
            match result {
                Ok(code) => serde_json::json!({"code":code}),
                Err(error) => serde_json::json!({"error":error}),
            }
        );
    }
}
