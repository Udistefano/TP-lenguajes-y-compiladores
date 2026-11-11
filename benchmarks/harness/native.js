const fs = require("node:fs");
const vm = require("node:vm");

const [file, warmupText, repetitionsText] = process.argv.slice(2);
const source = fs.readFileSync(file, "utf8");
const warmup = Number(warmupText);
const repetitions = Number(repetitionsText);
const samples = [];
let expected;
for (let i = -warmup; i < repetitions; i++) {
  global.gc();
  const lines = [];
  const start = process.hrtime.bigint();
  const script = new vm.Script(source);
  const ready = process.hrtime.bigint();
  script.runInNewContext({ print: value => lines.push(String(value)) });
  const end = process.hrtime.bigint();
  const output = lines.join("\n");
  if (expected === undefined) expected = output;
  if (output !== expected) throw new Error("La salida cambió entre muestras");
  if (i >= 0) samples.push({
    frontend_ms: Number(ready - start) / 1e6,
    execution_ms: Number(end - ready) / 1e6,
    total_ms: Number(end - start) / 1e6,
  });
}
console.log(JSON.stringify({ output: expected, samples, node: process.version, v8: process.versions.v8 }));
