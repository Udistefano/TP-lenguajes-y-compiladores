def make_adder(n):
    def add(x):
        return x + n
    return add


def make_counter():
    count = 0.0

    def tick():
        nonlocal count
        count = count + 1
        return count
    return tick


total = 0.0
i = 0.0
while i < 30000:
    add5 = make_adder(5.0)
    total = total + add5(i)
    i = i + 1
tick = make_counter()
j = 0.0
while j < 30000:
    tick()
    j = j + 1
print(total)
