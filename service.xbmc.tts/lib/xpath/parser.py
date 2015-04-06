import expr as X
from yappsrt import *


from string import *
import re

class XPathScanner(Scanner):
    patterns = [
        ("r'\\:'", re.compile('\\:')),
        ("r'node'", re.compile('node')),
        ("r'text'", re.compile('text')),
        ("r'comment'", re.compile('comment')),
        ("r'processing-instruction'", re.compile('processing-instruction')),
        ("r'\\,'", re.compile('\\,')),
        ("r'\\.'", re.compile('\\.')),
        ("r'\\$'", re.compile('\\$')),
        ("r'\\)'", re.compile('\\)')),
        ("r'\\('", re.compile('\\(')),
        ("r'\\]'", re.compile('\\]')),
        ("r'\\['", re.compile('\\[')),
        ("r'\\*'", re.compile('\\*')),
        ("r':'", re.compile(':')),
        ("r'\\.\\.'", re.compile('\\.\\.')),
        ("r'@'", re.compile('@')),
        ("r'::'", re.compile('::')),
        ("r'\\/\\/'", re.compile('\\/\\/')),
        ("r'\\/'", re.compile('\\/')),
        ("r'\\-'", re.compile('\\-')),
        ("'\\|'", re.compile('\\|')),
        ("r'and'", re.compile('and')),
        ("r'or'", re.compile('or')),
        ('\\s+', re.compile('\\s+')),
        ('END', re.compile('$')),
        ('FORWARD_AXIS_NAME', re.compile('child|descendant-or-self|attribute|self|descendant|following-sibling|following|namespace')),
        ('REVERSE_AXIS_NAME', re.compile('parent|preceding-sibling|preceding|ancestor-or-self|ancestor')),
        ('NCNAME', re.compile('[a-zA-Z_][a-zA-Z0-9_\\-\\.\\w]*(?!\\()')),
        ('FUNCNAME', re.compile('[a-zA-Z_][a-zA-Z0-9_\\-\\.\\w]*')),
        ('DQUOTE', re.compile('\\"(?:[^\\"])*\\"')),
        ('SQUOTE', re.compile("\\'(?:[^\\'])*\\'")),
        ('NUMBER', re.compile('((\\.[0-9]+)|([0-9]+(\\.[0-9]*)?))([eE][\\+\\-]?[0-9]+)?')),
        ('EQ_COMP', re.compile('\\!?\\=')),
        ('REL_COMP', re.compile('[\\<\\>]\\=?')),
        ('ADD_COMP', re.compile('[\\+\\-]')),
        ('MUL_COMP', re.compile('\\*|div|mod')),
    ]
    def __init__(self, str):
        Scanner.__init__(self,None,['\\s+'],str)

class XPath(Parser):
    def XPath(self):
        Expr = self.Expr()
        END = self._scan('END')
        return Expr

    def Expr(self):
        OrExpr = self.OrExpr()
        return OrExpr

    def OrExpr(self):
        AndExpr = self.AndExpr()
        Expr = AndExpr
        while self._peek("r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == "r'or'":
            self._scan("r'or'")
            AndExpr = self.AndExpr()
            Expr = X.OrExpr('or', Expr, AndExpr)
        return Expr

    def AndExpr(self):
        EqualityExpr = self.EqualityExpr()
        Expr = EqualityExpr
        while self._peek("r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == "r'and'":
            self._scan("r'and'")
            EqualityExpr = self.EqualityExpr()
            Expr = X.AndExpr('and', Expr, EqualityExpr)
        return Expr

    def EqualityExpr(self):
        RelationalExpr = self.RelationalExpr()
        Expr = RelationalExpr
        while self._peek('EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == 'EQ_COMP':
            EQ_COMP = self._scan('EQ_COMP')
            RelationalExpr = self.RelationalExpr()
            Expr = X.EqualityExpr(EQ_COMP, Expr, RelationalExpr)
        return Expr

    def RelationalExpr(self):
        AdditiveExpr = self.AdditiveExpr()
        Expr = AdditiveExpr
        while self._peek('REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == 'REL_COMP':
            REL_COMP = self._scan('REL_COMP')
            AdditiveExpr = self.AdditiveExpr()
            Expr = X.EqualityExpr(REL_COMP, Expr, AdditiveExpr)
        return Expr

    def AdditiveExpr(self):
        MultiplicativeExpr = self.MultiplicativeExpr()
        Expr = MultiplicativeExpr
        while self._peek('ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == 'ADD_COMP':
            ADD_COMP = self._scan('ADD_COMP')
            MultiplicativeExpr = self.MultiplicativeExpr()
            Expr = X.ArithmeticalExpr(ADD_COMP, Expr, MultiplicativeExpr)
        return Expr

    def MultiplicativeExpr(self):
        UnionExpr = self.UnionExpr()
        Expr = UnionExpr
        while self._peek('MUL_COMP', 'ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == 'MUL_COMP':
            MUL_COMP = self._scan('MUL_COMP')
            UnionExpr = self.UnionExpr()
            Expr = X.ArithmeticalExpr(MUL_COMP, Expr, UnionExpr)
        return Expr

    def UnionExpr(self):
        UnaryExpr = self.UnaryExpr()
        Expr = UnaryExpr
        while self._peek("'\\|'", 'MUL_COMP', 'ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == "'\\|'":
            self._scan("'\\|'")
            UnaryExpr = self.UnaryExpr()
            Expr = X.UnionExpr('|', Expr, UnaryExpr)
        return Expr

    def UnaryExpr(self):
        _token_ = self._peek("r'\\-'", "r'\\/'", "r'\\/\\/'", "r'\\('", 'FORWARD_AXIS_NAME', "r'@'", 'REVERSE_AXIS_NAME', "r'\\.\\.'", "r'\\$'", "r'\\.'", 'FUNCNAME', 'NUMBER', 'DQUOTE', 'SQUOTE', "r'processing-instruction'", "r'comment'", "r'text'", "r'node'", "r'\\*'", 'NCNAME')
        if _token_ == "r'\\-'":
            self._scan("r'\\-'")
            ValueExpr = self.ValueExpr()
            return X.NegationExpr(ValueExpr)
        else:
            ValueExpr = self.ValueExpr()
            return ValueExpr

    def ValueExpr(self):
        PathExpr = self.PathExpr()
        return PathExpr

    def PathExpr(self):
        _token_ = self._peek("r'\\/'", "r'\\/\\/'", "r'\\('", 'FORWARD_AXIS_NAME', "r'@'", 'REVERSE_AXIS_NAME', "r'\\.\\.'", "r'\\$'", "r'\\.'", 'FUNCNAME', 'NUMBER', 'DQUOTE', 'SQUOTE', "r'processing-instruction'", "r'comment'", "r'text'", "r'node'", "r'\\*'", 'NCNAME')
        if _token_ == "r'\\/'":
            self._scan("r'\\/'")
            path = None
            if self._peek("r'\\('", 'FORWARD_AXIS_NAME', "r'@'", 'REVERSE_AXIS_NAME', "r'\\.\\.'", "r'\\$'", "r'\\.'", 'FUNCNAME', 'NUMBER', 'DQUOTE', 'SQUOTE', "r'processing-instruction'", "r'comment'", "r'text'", "r'node'", "r'\\*'", 'NCNAME', "'\\|'", 'MUL_COMP', 'ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") not in ["'\\|'", 'MUL_COMP', 'ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'"]:
                RelativePathExpr = self.RelativePathExpr()
                path = RelativePathExpr
            return X.AbsolutePathExpr(path)
        elif _token_ == "r'\\/\\/'":
            self._scan("r'\\/\\/'")
            RelativePathExpr = self.RelativePathExpr()
            step = X.AxisStep('descendant-or-self')
            RelativePathExpr.steps.insert(0, step)
            return X.AbsolutePathExpr(RelativePathExpr)
        else:
            RelativePathExpr = self.RelativePathExpr()
            return RelativePathExpr

    def RelativePathExpr(self):
        StepExpr = self.StepExpr()
        steps = [StepExpr]
        while self._peek("r'\\/'", "r'\\/\\/'", "'\\|'", 'MUL_COMP', 'ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") in ["r'\\/'", "r'\\/\\/'"]:
            _token_ = self._peek("r'\\/'", "r'\\/\\/'")
            if _token_ == "r'\\/'":
                self._scan("r'\\/'")
            else:# == "r'\\/\\/'"
                self._scan("r'\\/\\/'")
                steps.append(X.AxisStep('descendant-or-self'))
            StepExpr = self.StepExpr()
            steps.append(StepExpr)
        return X.PathExpr(steps)

    def StepExpr(self):
        _token_ = self._peek("r'\\('", 'FORWARD_AXIS_NAME', "r'@'", 'REVERSE_AXIS_NAME', "r'\\.\\.'", "r'\\$'", "r'\\.'", 'FUNCNAME', 'NUMBER', 'DQUOTE', 'SQUOTE', "r'processing-instruction'", "r'comment'", "r'text'", "r'node'", "r'\\*'", 'NCNAME')
        if _token_ not in ["r'\\('", "r'\\$'", "r'\\.'", 'FUNCNAME', 'NUMBER', 'DQUOTE', 'SQUOTE']:
            AxisStep = self.AxisStep()
            return AxisStep
        else:
            FilterExpr = self.FilterExpr()
            return FilterExpr

    def AxisStep(self):
        _token_ = self._peek('FORWARD_AXIS_NAME', "r'@'", 'REVERSE_AXIS_NAME', "r'\\.\\.'", "r'processing-instruction'", "r'comment'", "r'text'", "r'node'", "r'\\*'", 'NCNAME')
        if _token_ not in ['REVERSE_AXIS_NAME', "r'\\.\\.'"]:
            ForwardStep = self.ForwardStep()
            step = ForwardStep
        else:# in ['REVERSE_AXIS_NAME', "r'\\.\\.'"]
            ReverseStep = self.ReverseStep()
            step = ReverseStep
        expr = X.AxisStep(*step)
        if self._peek("r'\\['", "r'\\/'", "r'\\/\\/'", "'\\|'", 'MUL_COMP', 'ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == "r'\\['":
            PredicateList = self.PredicateList()
            expr = X.PredicateList(expr, PredicateList, step[0])
        return expr

    def ForwardStep(self):
        _token_ = self._peek('FORWARD_AXIS_NAME', "r'@'", "r'processing-instruction'", "r'comment'", "r'text'", "r'node'", "r'\\*'", 'NCNAME')
        if _token_ == 'FORWARD_AXIS_NAME':
            ForwardAxis = self.ForwardAxis()
            NodeTest = self.NodeTest()
            return [ForwardAxis, NodeTest]
        else:
            AbbrevForwardStep = self.AbbrevForwardStep()
            return AbbrevForwardStep

    def ForwardAxis(self):
        FORWARD_AXIS_NAME = self._scan('FORWARD_AXIS_NAME')
        self._scan("r'::'")
        return FORWARD_AXIS_NAME

    def AbbrevForwardStep(self):
        axis = 'child'
        if self._peek("r'@'", "r'processing-instruction'", "r'comment'", "r'text'", "r'node'", "r'\\*'", 'NCNAME') == "r'@'":
            self._scan("r'@'")
            axis = 'attribute'
        NodeTest = self.NodeTest()
        return [axis, NodeTest]

    def ReverseStep(self):
        _token_ = self._peek('REVERSE_AXIS_NAME', "r'\\.\\.'")
        if _token_ == 'REVERSE_AXIS_NAME':
            ReverseAxis = self.ReverseAxis()
            NodeTest = self.NodeTest()
            return [ReverseAxis, NodeTest]
        else:# == "r'\\.\\.'"
            AbbrevReverseStep = self.AbbrevReverseStep()
            return AbbrevReverseStep

    def ReverseAxis(self):
        REVERSE_AXIS_NAME = self._scan('REVERSE_AXIS_NAME')
        self._scan("r'::'")
        return REVERSE_AXIS_NAME

    def AbbrevReverseStep(self):
        self._scan("r'\\.\\.'")
        return ['parent', None]

    def NodeTest(self):
        _token_ = self._peek("r'processing-instruction'", "r'comment'", "r'text'", "r'node'", "r'\\*'", 'NCNAME')
        if _token_ not in ["r'\\*'", 'NCNAME']:
            KindTest = self.KindTest()
            return KindTest
        else:# in ["r'\\*'", 'NCNAME']
            NameTest = self.NameTest()
            return NameTest

    def NameTest(self):
        prefix = None
        WildcardOrNCName = self.WildcardOrNCName()
        localpart = WildcardOrNCName
        if self._peek("r':'", "r'\\['", "r'\\/'", "r'\\/\\/'", "'\\|'", 'MUL_COMP', 'ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == "r':'":
            self._scan("r':'")
            WildcardOrNCName = self.WildcardOrNCName()
            prefix = localpart
            localpart = WildcardOrNCName
        return X.NameTest(prefix, localpart)

    def WildcardOrNCName(self):
        _token_ = self._peek("r'\\*'", 'NCNAME')
        if _token_ == "r'\\*'":
            self._scan("r'\\*'")
            return '*'
        else:# == 'NCNAME'
            NCNAME = self._scan('NCNAME')
            return NCNAME

    def FilterExpr(self):
        PrimaryExpr = self.PrimaryExpr()
        if self._peek("r'\\['", "r'\\/'", "r'\\/\\/'", "'\\|'", 'MUL_COMP', 'ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == "r'\\['":
            PredicateList = self.PredicateList()
            PrimaryExpr = X.PredicateList(PrimaryExpr,PredicateList)
        return PrimaryExpr

    def PredicateList(self):
        Predicate = self.Predicate()
        predicates = [Predicate]
        while self._peek("r'\\['", "r'\\/'", "r'\\/\\/'", "'\\|'", 'MUL_COMP', 'ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == "r'\\['":
            Predicate = self.Predicate()
            predicates.append(Predicate)
        return predicates

    def Predicate(self):
        self._scan("r'\\['")
        Expr = self.Expr()
        self._scan("r'\\]'")
        return Expr

    def PrimaryExpr(self):
        _token_ = self._peek("r'\\('", "r'\\$'", "r'\\.'", 'FUNCNAME', 'NUMBER', 'DQUOTE', 'SQUOTE')
        if _token_ not in ["r'\\('", "r'\\$'", "r'\\.'", 'FUNCNAME']:
            Literal = self.Literal()
            return X.LiteralExpr(Literal)
        elif _token_ == "r'\\$'":
            VariableReference = self.VariableReference()
            return VariableReference
        elif _token_ == "r'\\('":
            self._scan("r'\\('")
            Expr = self.Expr()
            self._scan("r'\\)'")
            return Expr
        elif _token_ == "r'\\.'":
            ContextItemExpr = self.ContextItemExpr()
            return ContextItemExpr
        else:# == 'FUNCNAME'
            FunctionCall = self.FunctionCall()
            return FunctionCall

    def VariableReference(self):
        self._scan("r'\\$'")
        QName = self.QName()
        return X.VariableReference(*QName)

    def ContextItemExpr(self):
        self._scan("r'\\.'")
        return X.AxisStep('self')

    def FunctionCall(self):
        FUNCNAME = self._scan('FUNCNAME')
        self._scan("r'\\('")
        args = []
        if self._peek("r'\\,'", "r'\\)'", "r'\\-'", "r'\\/'", "r'\\/\\/'", "r'\\('", 'FORWARD_AXIS_NAME', "r'@'", 'REVERSE_AXIS_NAME', "r'\\.\\.'", "r'\\$'", "r'\\.'", 'FUNCNAME', 'NUMBER', 'DQUOTE', 'SQUOTE', "r'processing-instruction'", "r'comment'", "r'text'", "r'node'", "r'\\*'", 'NCNAME') not in ["r'\\,'", "r'\\)'"]:
            Expr = self.Expr()
            args.append(Expr)
            while self._peek("r'\\,'", "r'\\)'") == "r'\\,'":
                self._scan("r'\\,'")
                Expr = self.Expr()
                args.append(Expr)
        self._scan("r'\\)'")
        return X.Function(FUNCNAME, args)

    def KindTest(self):
        _token_ = self._peek("r'processing-instruction'", "r'comment'", "r'text'", "r'node'")
        if _token_ == "r'processing-instruction'":
            PITest = self.PITest()
            return PITest
        elif _token_ == "r'comment'":
            CommentTest = self.CommentTest()
            return CommentTest
        elif _token_ == "r'text'":
            TextTest = self.TextTest()
            return TextTest
        else:# == "r'node'"
            AnyKindTest = self.AnyKindTest()
            return AnyKindTest

    def PITest(self):
        self._scan("r'processing-instruction'")
        name = None
        self._scan("r'\\('")
        if self._peek('NCNAME', "r'\\)'", 'DQUOTE', 'SQUOTE') != "r'\\)'":
            _token_ = self._peek('NCNAME', 'DQUOTE', 'SQUOTE')
            if _token_ == 'NCNAME':
                NCNAME = self._scan('NCNAME')
                name = NCNAME
            else:# in ['DQUOTE', 'SQUOTE']
                StringLiteral = self.StringLiteral()
                name = StringLiteral
        self._scan("r'\\)'")
        return X.PITest(name)

    def CommentTest(self):
        self._scan("r'comment'")
        self._scan("r'\\('")
        self._scan("r'\\)'")
        return X.CommentTest()

    def TextTest(self):
        self._scan("r'text'")
        self._scan("r'\\('")
        self._scan("r'\\)'")
        return X.TextTest()

    def AnyKindTest(self):
        self._scan("r'node'")
        self._scan("r'\\('")
        self._scan("r'\\)'")
        return X.AnyKindTest()

    def Literal(self):
        _token_ = self._peek('NUMBER', 'DQUOTE', 'SQUOTE')
        if _token_ == 'NUMBER':
            NumericLiteral = self.NumericLiteral()
            return NumericLiteral
        else:# in ['DQUOTE', 'SQUOTE']
            StringLiteral = self.StringLiteral()
            return StringLiteral

    def NumericLiteral(self):
        NUMBER = self._scan('NUMBER')
        return float(NUMBER)

    def StringLiteral(self):
        _token_ = self._peek('DQUOTE', 'SQUOTE')
        if _token_ == 'DQUOTE':
            DQUOTE = self._scan('DQUOTE')
            return DQUOTE[1:-1]
        else:# == 'SQUOTE'
            SQUOTE = self._scan('SQUOTE')
            return SQUOTE[1:-1]

    def QName(self):
        NCNAME = self._scan('NCNAME')
        name = NCNAME
        if self._peek("r'\\:'", "r'\\['", "r'\\/'", "r'\\/\\/'", "'\\|'", 'MUL_COMP', 'ADD_COMP', 'REL_COMP', 'EQ_COMP', "r'and'", "r'or'", 'END', "r'\\]'", "r'\\)'", "r'\\,'") == "r'\\:'":
            self._scan("r'\\:'")
            NCNAME = self._scan('NCNAME')
            return (name, NCNAME)
        return (None, name)


def parse(rule, text):
    P = XPath(XPathScanner(text))
    return wrap_error_reporter(P, rule)

if __name__ == '__main__':
    from sys import argv, stdin
    if len(argv) >= 2:
        if len(argv) >= 3:
            f = open(argv[2],'r')
        else:
            f = stdin
        print parse(argv[1], f.read())
    else: print 'Args:  <rule> [<filename>]'
