"""Generic finite-expression/transition evaluator: no Cyclic type or ontology claim."""
def evaluate(expr, env):
    if isinstance(expr, str):
        return env[expr]
    op, *args = expr
    if op == "inv":
        p = evaluate(args[0], env)
        return [next(i for i,v in enumerate(p) if v == x) for x in range(len(p))]
    if op == "compose":
        p, q = [evaluate(arg, env) for arg in args]
        return [p[value] for value in q]
    raise ValueError("expression")

def simulate(a,h,r):
    env = {"a":a,"h":h,"r":r}
    env["b"] = evaluate(("compose","r",("compose","h",("inv","r"))),env)
    c = evaluate(("compose","a",("compose","b",("compose",("inv","a"),("inv","b")))),env)
    # A general finite table can encode this object-law transition.
    table = {k:((k+3)%9) for k in range(9)}
    k, states = 0, []
    for _ in range(4):
        q,x = k//3,0
        for __ in range(q):
            x = c[x]
        states.append({"k":k,"q":q,"vertex":k%3,"x":x})
        k = table[k]
    return {"c":c,"states":states,"formal_novelty":"FAIL",
            "limit":"computability, not attribution of independent H agency"}

