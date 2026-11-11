function divisible(n, d) {
  let r = n;
  while (r >= d) r = r - d;
  return r === 0;
}
let acc = "";
let i = 1;
while (i <= 400) {
  if (divisible(i, 3) && divisible(i, 5)) acc = acc + "FizzBuzz";
  else if (divisible(i, 3)) acc = acc + "Fizz";
  else if (divisible(i, 5)) acc = acc + "Buzz";
  else acc = acc + ".";
  i = i + 1;
}
print(acc);
