function es_primo(n) {
  if (n < 2) return false;
  let d = 2;
  while (d * d <= n) {
    let r = n;
    while (r >= d) r = r - d;
    if (r === 0) return false;
    d = d + 1;
  }
  return true;
}
let cuenta = 0;
let i = 2;
while (i <= 300) {
  if (es_primo(i)) cuenta = cuenta + 1;
  i = i + 1;
}
print(cuenta);
