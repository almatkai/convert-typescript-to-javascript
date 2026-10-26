use serde_json::{json, Value};
use tezbar_convert_typescript_to_javascript::compiler::convert;
#[test]
fn required_exact_locked_babel_parity() {
    let cases: Vec<Value> = serde_json::from_str(include_str!("locked-babel.json")).unwrap();
    let mut failures = Vec::new();
    for case in &cases {
        let actual = match convert(case["source"].as_str().unwrap()) {
            Ok(code) => json!({"code":code}),
            Err(error) => json!({"error":error}),
        };
        if actual != case["expected"] {
            failures.push(json!({"name":case["name"],"source":case["source"],"babel":case["expected"],"native":actual}));
        }
    }
    assert!(
        failures.is_empty(),
        "Exact Babel parity {}/{}. Required gate FAILED:\n{}",
        cases.len() - failures.len(),
        cases.len(),
        serde_json::to_string_pretty(&failures).unwrap()
    );
}
