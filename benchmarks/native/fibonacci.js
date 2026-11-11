function fib(n) {
  if (n < 2) return n;
  return fib(n - 1) + fib(n - 2);
}
let total = 0;
let i = 0;
while (i < 21) {
  total = total + fib(i);
  i = i + 1;
}
print(total);
