
const WebSocket = require("ws");
const ws = new WebSocket("ws://127.0.0.1:9222/devtools/page/4319F7AE6CECC784EC82D3A4327F177F");

const errors = [];
ws.on("open", () => {
    // Enable Runtime to capture console messages
    ws.send(JSON.stringify({id: 1, method: "Runtime.enable"}));
    ws.send(JSON.stringify({id: 2, method: "Runtime.runIfWaitingForDebugger"}));
});

ws.on("message", (data) => {
    const msg = JSON.parse(data.toString());
    // Capture console API calls (console.error, console.warn, etc.)
    if (msg.method === "Runtime.consoleAPICalled") {
        const args = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(" ");
        if (msg.params.type === "error" || msg.params.type === "warning") {
            errors.push(`[${msg.params.type}] ${args}`);
        }
    }
    // Capture exceptions
    if (msg.method === "Runtime.exceptionThrown") {
        const exc = msg.params.exceptionDetails;
        errors.push(`[EXCEPTION] ${exc.text || exc.exception?.description || JSON.stringify(exc)}`);
    }
});

// After 3 seconds, reload the page and wait for errors
setTimeout(() => {
    ws.send(JSON.stringify({id: 3, method: "Page.reload"}));
}, 500);

setTimeout(() => {
    console.log(JSON.stringify(errors, null, 2));
    ws.close();
    process.exit(0);
}, 5000);
