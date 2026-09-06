

#clase base para todos los nodos del árbol. Cada nodo debe implementar el método accept() para permitir que un visitante recorra el árbol y realice operaciones sobre los nodos.
class Node:
    def accept(self, visitor):
        raise NotImplementedError(
            f"{type(self).__name__} no implementa accept()"
        )

# clase Visitor define la interfaz para los visitantes que pueden recorrer el árbol de nodos y realizar operaciones sobre ellos.
class Visitor:
    def visit_literal(self, expression):
        raise NotImplementedError()

    def visit_unary(self, expression):
        raise NotImplementedError()

    def visit_binary(self, expression):
        raise NotImplementedError()

    def visit_grouping(self, expression):
        raise NotImplementedError()

#clase representa un literal, que puede ser un número, una cadena o un valor booleano.
class Literal(Node):
    def __init__(self, value):
        self.value = value

    def accept(self, visitor):
        return visitor.visit_literal(self)

#clase representa una expresión unaria, que consiste en un operador y un operando.
class Unary(Node):
    def __init__(self, operator, operand):
        self.operator = operator
        self.operand = operand

    def accept(self, visitor):
        return visitor.visit_unary(self)

# clase representa una expresión binaria, que consiste en un operador y dos operandos.
class Binary(Node):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right
    def accept(self, visitor):
        return visitor.visit_binary(self)

# clase representa una expresión entre paréntesis. 
class Grouping(Node):
    def __init__(self, expression):
        self.expression = expression

    def accept(self, visitor):
        return visitor.visit_grouping(self)