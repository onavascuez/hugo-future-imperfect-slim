"""Conversor mínimo de SCSS a CSS para assets/scss/main.scss de hugo-future-imperfect-slim.

No es un compilador de Sass general: cubre solo lo que usa ese fichero
(variables, anidamiento con &, @mixin/@include con @content, @each sobre listas,
@if/@else de existencia, interpolación #{} y darken() sobre hsl).
Uso: python3 scss2css.py main.scss main.css
"""
import re
import sys


def strip_comments(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif src.startswith("//", i) and (i == 0 or src[i - 1] in " \t\n"):
            j = src.find("\n", i)
            i = n if j < 0 else j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def parse(src, i=0):
    """Devuelve (nodos, posición). Nodo: ('decl', texto) o ('block', preludio, hijos)."""
    nodes, buf, n, depth = [], [], len(src), 0
    while i < n:
        c = src[i]
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            buf.append(src[i:j + 1])
            i = j + 1
            continue
        if src.startswith("#{", i):
            j = src.find("}", i)
            buf.append(src[i:j + 1])
            i = j + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        if depth == 0 and c == ";":
            text = "".join(buf).strip()
            if text:
                nodes.append(("decl", text))
            buf = []
        elif depth == 0 and c == "{":
            children, i = parse(src, i + 1)
            nodes.append(("block", " ".join("".join(buf).split()), children))
            buf = []
            continue
        elif depth == 0 and c == "}":
            text = "".join(buf).strip()
            if text:
                nodes.append(("decl", text))
            return nodes, i + 1
        else:
            buf.append(c)
        i += 1
    text = "".join(buf).strip()
    if text:
        nodes.append(("decl", text))
    return nodes, i


def split_top(text, sep=","):
    parts, buf, depth, i, n = [], [], 0, 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            buf.append(text[i:j + 1])
            i = j + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        if c == sep and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    last = "".join(buf).strip()
    if last:
        parts.append(last)
    return parts


def darken(match):
    color, amount = split_top(match.group(1))
    m = re.match(r"hsl\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%\s*\)", color)
    if not m:
        raise SystemExit("darken() sobre un color que no es hsl: " + color)
    light = max(0.0, float(m.group(3)) - float(amount.rstrip("%")))
    return "hsl(%s, %s%%, %g%%)" % (m.group(1), m.group(2), light)


VAR = re.compile(r"\$([A-Za-z0-9_-]+)")


def subst(text, env):
    def interp(m):
        return subst(m.group(1), env)
    text = re.sub(r"#\{([^}]*)\}", interp, text)

    def var(m):
        name = m.group(1)
        if name not in env:
            raise SystemExit("variable sin definir: $" + name)
        return env[name] if env[name] is not None else ""
    for _ in range(5):
        new = VAR.sub(var, text)
        if new == text:
            break
        text = new
    return re.sub(r"darken\(((?:[^()]|\([^()]*\))*)\)", darken, text)


def unquote(value):
    return value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'" else value


class Compiler:
    def __init__(self):
        self.mixins = {}
        self.out = []          # (media, selector, [declaraciones])

    def emit(self, media, selector, decl):
        if self.out and self.out[-1][0] == media and self.out[-1][1] == selector:
            self.out[-1][2].append(decl)
        else:
            self.out.append((media, selector, [decl]))

    def run(self, nodes, env, selector=None, media=None, content=None):
        i = 0
        while i < len(nodes):
            node = nodes[i]
            i += 1
            if node[0] == "decl":
                text = node[1]
                if text.startswith("$"):
                    name, value = text[1:].split(":", 1)
                    env[name.strip()] = subst(" ".join(value.split()), env) if "(" not in value[:3] and not value.strip().startswith("(") else " ".join(value.split())
                elif text.startswith("@include"):
                    self.include(text[len("@include"):].strip(), None, env, selector, media)
                elif text == "@content":
                    if content:
                        c_nodes, c_env = content
                        self.run(c_nodes, c_env, selector, media, None)
                elif text.startswith("@"):
                    self.out.append((None, None, [subst(text, env) + ";"]))
                else:
                    if selector is None:
                        raise SystemExit("declaración fuera de una regla: " + text)
                    prop, value = text.split(":", 1)
                    self.emit(media, selector, "%s: %s;" % (subst(prop.strip(), env), subst(" ".join(value.split()), env)))
                continue
            _, prelude, children = node
            if prelude.startswith("@mixin"):
                m = re.match(r"@mixin\s+([\w-]+)\s*(?:\((.*)\))?$", prelude)
                self.mixins[m.group(1)] = (split_top(m.group(2) or ""), children)
            elif prelude.startswith("@include"):
                self.include(prelude[len("@include"):].strip(), (children, env), env, selector, media)
            elif prelude.startswith("@each"):
                m = re.match(r"@each\s+(.+?)\s+in\s+(.+)$", prelude)
                names = [v.strip().lstrip("$") for v in m.group(1).split(",")]
                source = subst(m.group(2), env).strip()
                if source.startswith("("):
                    source = source[1:-1]
                for item in split_top(source):
                    local = dict(env)
                    if len(names) == 1:
                        local[names[0]] = unquote(item)
                    else:
                        values = split_top(item[1:-1] if item.startswith("(") else item)
                        for k, name in enumerate(names):
                            local[name] = values[k] if k < len(values) else None
                    self.run(children, local, selector, media, content)
            elif prelude.startswith("@if"):
                cond = prelude[len("@if"):].strip()
                if cond.startswith("(") and cond.endswith(")"):
                    cond = cond[1:-1].strip()
                truthy = self.truthy(cond, env)
                otherwise = None
                if i < len(nodes) and nodes[i][0] == "block" and nodes[i][1].startswith("@else"):
                    otherwise = nodes[i][2]
                    i += 1
                if truthy:
                    self.run(children, env, selector, media, content)
                elif otherwise is not None:
                    self.run(otherwise, env, selector, media, content)
            elif prelude.startswith("@media"):
                query = subst(prelude[len("@media"):].strip(), env)
                new_media = query if media is None else "%s and %s" % (media, query)
                self.run(children, dict(env), selector, new_media, content)
            elif prelude.startswith("@"):
                # @font-face, @keyframes… tal cual
                self.out.append((None, None, [subst(prelude, env) + " {" + self.raw(children, env) + "}"]))
            else:
                sel = subst(prelude, env)
                parts = []
                for child in split_top(sel):
                    if selector is None:
                        parts.append(child)
                    else:
                        for parent in split_top(selector):
                            parts.append(child.replace("&", parent) if "&" in child else parent + " " + child)
                self.run(children, dict(env), ", ".join(parts), media, content)

    def truthy(self, cond, env):
        m = re.match(r"index\(\s*\$([\w-]+)\s*,\s*\$([\w-]+)\s*\)$", cond)
        if m:
            items = [unquote(x) for x in split_top(env[m.group(1)].strip()[1:-1])]
            return unquote(env[m.group(2)] or "") in items
        m = re.match(r"\$([\w-]+)$", cond)
        if m:
            return env.get(m.group(1)) not in (None, "", "null", "false")
        raise SystemExit("@if no soportado: " + cond)

    def include(self, call, content, env, selector, media):
        m = re.match(r"([\w-]+)\s*(?:\((.*)\))?$", call, re.S)
        name, args = m.group(1), split_top(m.group(2) or "")
        if name not in self.mixins:
            raise SystemExit("mixin sin definir: " + name)
        params, body = self.mixins[name]
        local = dict(env)
        for k, param in enumerate(params):
            pname, _, default = param.partition(":")
            pname = pname.strip().lstrip("$")
            if k < len(args):
                local[pname] = subst(args[k], env)
            else:
                default = default.strip()
                local[pname] = None if default in ("", "null") else default
        self.run(body, local, selector, media, content)

    def raw(self, nodes, env):
        parts = []
        for node in nodes:
            if node[0] == "decl":
                parts.append(subst(node[1], env) + ";")
            else:
                parts.append(subst(node[1], env) + " {" + self.raw(node[2], env) + "}")
        return " ".join(parts)

    def css(self):
        lines = []
        for media, selector, decls in self.out:
            if selector is None:
                lines.extend(decls)
                continue
            rule = "%s {\n  %s\n}" % (selector, "\n  ".join(decls))
            if media:
                rule = "@media %s {\n%s\n}" % (media, "\n".join("  " + l for l in rule.split("\n")))
            lines.append(rule)
        return "\n\n".join(lines) + "\n"


def main(src_path, dst_path):
    src = open(src_path, encoding="utf-8").read()
    nodes, _ = parse(strip_comments(src))
    compiler = Compiler()
    compiler.run(nodes, {})
    header = ("/*! Future Imperfect by HTML5 UP | html5up.net | CCA 3.0 license (html5up.net/license)\n"
              " * Slimmed/Cleaned/Modernized for Hugo by @pacollins\n"
              " * Generado desde assets/scss/main.scss; no editar a mano. */\n\n")
    css = compiler.css()
    if "$" in re.sub(r"\"[^\"]*\"|'[^']*'", "", css) or "@include" in css or "@mixin" in css or "#{" in css:
        raise SystemExit("quedan restos de Sass en la salida")
    if css.count("{") != css.count("}"):
        raise SystemExit("llaves desbalanceadas")
    open(dst_path, "w", encoding="utf-8").write(header + css)
    print("reglas:", len(compiler.out), "bytes:", len(css))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
