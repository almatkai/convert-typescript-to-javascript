use tezbar_convert_typescript_to_javascript::compiler::{convert, MAX_INPUT};
#[test]
fn input_structure_and_output_bounds() {
    assert!(convert(&"x".repeat(MAX_INPUT + 1))
        .unwrap_err()
        .contains("64 KiB"));
    assert!(convert(&format!("{}1{}", "(".repeat(129), ")".repeat(129)))
        .unwrap_err()
        .contains("structural complexity"));
    assert!(convert(&format!("const x = \"{}\";", "a".repeat(4097)))
        .unwrap_err()
        .contains("4096 scalars"));
    let mut source = format!("const x={}", "{a:".repeat(120));
    source.push('{');
    for i in 0..3000 {
        source.push_str(&format!("x{i}:1,"));
    }
    source.push('}');
    source.push_str(&"}".repeat(120));
    source.push(';');
    assert!(source.len() < MAX_INPUT);
    assert!(convert(&source).unwrap_err().contains("512 KiB"));
}
