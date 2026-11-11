let total = 0;
let i = 1;
while (i <= 100000) {
  total = total + i * 2 - i;
  i = i + 1;
}
print(total);
