use tezbar_convert_typescript_to_javascript::adapter::Adapter;
fn main() {
    // Fixed owned SDK runtime workers; no detached transformer or helper process.
    // The parser and codegen are synchronous and obey byte/structure guards.
    std::panic::set_hook(Box::new(|_| eprintln!("Native transformation failed")));
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(2)
        .thread_stack_size(64 * 1024 * 1024)
        .enable_all()
        .build()
        .expect("SDK runtime initialization");
    if let Err(error) = runtime.block_on(tezbar_extension_sdk::serve(Adapter::default())) {
        eprintln!("Extension protocol failed: {error}");
        std::process::exit(1);
    }
}
