// usage: node mgmt.mjs METHOD PATH [jsonbody]
process.env.DATA_DIR ||= process.env.HOME + "/.omniroute";
const { getCliToken, CLI_TOKEN_HEADER } = await import(process.env.HOME + "/.local/lib/node_modules/omniroute/bin/cli/utils/cliToken.mjs");
const tok = await getCliToken();
const [m, p, b] = process.argv.slice(2);
const r = await fetch("http://127.0.0.1:20128" + p, { method: m, redirect: "error", headers: { [CLI_TOKEN_HEADER]: tok, "content-type": "application/json" }, body: b });
const t = await r.text();
console.log(r.status, t.slice(0, Number(process.env.MAXC || 3000)));
