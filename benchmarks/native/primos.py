def es_primo(n):
    if n < 2:
        return False
    d = 2.0
    while d * d <= n:
        r = n
        while r >= d:
            r = r - d
        if r == 0:
            return False
        d = d + 1
    return True


cuenta = 0.0
i = 2.0
while i <= 300:
    if es_primo(i):
        cuenta = cuenta + 1
    i = i + 1
print(cuenta)
