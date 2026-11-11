def divisible(n, d):
    r = n
    while r >= d:
        r = r - d
    return r == 0


acc = ""
i = 1.0
while i <= 400:
    if divisible(i, 3.0) and divisible(i, 5.0):
        acc = acc + "FizzBuzz"
    elif divisible(i, 3.0):
        acc = acc + "Fizz"
    elif divisible(i, 5.0):
        acc = acc + "Buzz"
    else:
        acc = acc + "."
    i = i + 1
print(acc)
