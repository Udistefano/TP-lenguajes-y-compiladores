function make_adder(n) {
  function add(x) { return x + n; }
  return add;
}
function make_counter() {
  let count = 0;
  function tick() { count = count + 1; return count; }
  return tick;
}
let total = 0;
let i = 0;
while (i < 30000) {
  const add5 = make_adder(5);
  total = total + add5(i);
  i = i + 1;
}
const tick = make_counter();
let j = 0;
while (j < 30000) { tick(); j = j + 1; }
print(total);
