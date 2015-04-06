import xpath.expr as X
from xpath.yappsrt import *

%%

parser XPath:
    option: 'no-support-module'

    ignore:     r'\s+'
    token END:  r'$'

    token FORWARD_AXIS_NAME:
        r'child|descendant-or-self|attribute|self|descendant|following-sibling|following|namespace'
    token REVERSE_AXIS_NAME:
        r'parent|preceding-sibling|preceding|ancestor-or-self|ancestor'

    # Dire hack here, since yapps2 has only one token of lookahead: NCNAME
    # does not match when followed by a open paren.
    token NCNAME:   r'[a-zA-Z_][a-zA-Z0-9_\-\.\w]*(?!\()'
    token FUNCNAME: r'[a-zA-Z_][a-zA-Z0-9_\-\.\w]*'

    token DQUOTE:   r'\"(?:[^\"])*\"'
    token SQUOTE:   r"\'(?:[^\'])*\'"
    token NUMBER:   r'((\.[0-9]+)|([0-9]+(\.[0-9]*)?))([eE][\+\-]?[0-9]+)?'
    token EQ_COMP:  r'\!?\='
    token REL_COMP: r'[\<\>]\=?'
    token ADD_COMP: r'[\+\-]'
    token MUL_COMP: r'\*|div|mod'

    rule XPath:
          Expr END                      {{ return Expr }}

    rule Expr:
          OrExpr                        {{ return OrExpr }}

    rule OrExpr:
          AndExpr                       {{ Expr = AndExpr }}
          (
            r'or' AndExpr
            {{ Expr = X.OrExpr('or', Expr, AndExpr) }}
          )*                            {{ return Expr }}

    rule AndExpr:
          EqualityExpr                  {{ Expr = EqualityExpr }}
          (
            r'and' EqualityExpr
            {{ Expr = X.AndExpr('and', Expr, EqualityExpr) }}
          )*                            {{ return Expr }}

    rule EqualityExpr:
          RelationalExpr                {{ Expr = RelationalExpr }}
          (
            EQ_COMP
            RelationalExpr
            {{ Expr = X.EqualityExpr(EQ_COMP, Expr, RelationalExpr) }}
          )*                            {{ return Expr }}

    rule RelationalExpr:
          AdditiveExpr                  {{ Expr = AdditiveExpr }}
          (
            REL_COMP
            AdditiveExpr
            {{ Expr = X.EqualityExpr(REL_COMP, Expr, AdditiveExpr) }}
          )*                            {{ return Expr }}

    rule AdditiveExpr:
          MultiplicativeExpr            {{ Expr = MultiplicativeExpr }}
          (
            ADD_COMP
            MultiplicativeExpr
            {{ Expr = X.ArithmeticalExpr(ADD_COMP, Expr, MultiplicativeExpr) }}
          )*                            {{ return Expr }}

    rule MultiplicativeExpr:
          UnionExpr                     {{ Expr = UnionExpr }}
          (
            MUL_COMP
            UnionExpr
            {{ Expr = X.ArithmeticalExpr(MUL_COMP, Expr, UnionExpr) }}
          )*                            {{ return Expr }}

    rule UnionExpr:
          UnaryExpr                     {{ Expr = UnaryExpr }}
          (
            '\|' UnaryExpr
            {{ Expr = X.UnionExpr('|', Expr, UnaryExpr) }}
          )*                            {{ return Expr }}

    rule UnaryExpr:
          r'\-' ValueExpr               {{ return X.NegationExpr(ValueExpr) }}
        | ValueExpr                     {{ return ValueExpr }}

    rule ValueExpr:
          PathExpr                      {{ return PathExpr }}

    rule PathExpr:
          r'\/'                         {{ path = None }}
          [
            RelativePathExpr            {{ path = RelativePathExpr }}
          ]                             {{ return X.AbsolutePathExpr(path) }}
        | r'\/\/' RelativePathExpr
                        {{ step = X.AxisStep('descendant-or-self') }}
                        {{ RelativePathExpr.steps.insert(0, step) }}
                        {{ return X.AbsolutePathExpr(RelativePathExpr) }}
        | RelativePathExpr              {{ return RelativePathExpr }}

    rule RelativePathExpr:
          StepExpr                      {{ steps = [StepExpr] }}
          (
            (
                r'\/'
              | r'\/\/'
                {{ steps.append(X.AxisStep('descendant-or-self')) }}
            )
            StepExpr                    {{ steps.append(StepExpr) }}
          )*
                                        {{ return X.PathExpr(steps) }}

    rule StepExpr:
          AxisStep                      {{ return AxisStep }}
        | FilterExpr                    {{ return FilterExpr }}

    rule AxisStep:
        (
            ForwardStep                 {{ step = ForwardStep }}
          | ReverseStep                 {{ step = ReverseStep }}
        )                               {{ expr = X.AxisStep(*step) }}
        [
          PredicateList
          {{ expr = X.PredicateList(expr, PredicateList, step[0]) }}
        ]
                                        {{ return expr }}

    rule ForwardStep:
          ForwardAxis NodeTest          {{ return [ForwardAxis, NodeTest] }}
        | AbbrevForwardStep             {{ return AbbrevForwardStep }}

    rule ForwardAxis:
          FORWARD_AXIS_NAME r'::'       {{ return FORWARD_AXIS_NAME }}

    rule AbbrevForwardStep:
                                        {{ axis = 'child' }}
          [
            r'@'                        {{ axis = 'attribute' }}
          ]
          NodeTest                      {{ return [axis, NodeTest] }}

    rule ReverseStep:
          ReverseAxis NodeTest          {{ return [ReverseAxis, NodeTest] }}
        | AbbrevReverseStep             {{ return AbbrevReverseStep }}

    rule ReverseAxis:
          REVERSE_AXIS_NAME r'::'       {{ return REVERSE_AXIS_NAME }}

    rule AbbrevReverseStep:
          r'\.\.'                       {{ return ['parent', None] }}

    rule NodeTest:
          KindTest                      {{ return KindTest }}
        | NameTest                      {{ return NameTest }}

    rule NameTest:
          # We also support the XPath 2.0 <name>:*.
                                        {{ prefix = None }}
          WildcardOrNCName              {{ localpart = WildcardOrNCName }}
          [
            r':' WildcardOrNCName       {{ prefix = localpart }}
                                        {{ localpart = WildcardOrNCName }}
          ]
          {{ return X.NameTest(prefix, localpart) }}

    rule WildcardOrNCName:
          r'\*'                         {{ return '*' }}
        | NCNAME                        {{ return NCNAME }}

    rule FilterExpr:
          PrimaryExpr
          [
            PredicateList
            {{ PrimaryExpr = X.PredicateList(PrimaryExpr,PredicateList) }}
          ]                             {{ return PrimaryExpr }}

    rule PredicateList:
          Predicate                     {{ predicates = [Predicate] }}
          (
            Predicate                   {{ predicates.append(Predicate) }}
          )*                            {{ return predicates }}

    rule Predicate:
          r'\[' Expr r'\]'              {{ return Expr }}

    rule PrimaryExpr:
          Literal                       {{ return X.LiteralExpr(Literal) }}
        | VariableReference             {{ return VariableReference }}
        | r'\(' Expr r'\)'              {{ return Expr }}
        | ContextItemExpr               {{ return ContextItemExpr }}
        | FunctionCall                  {{ return FunctionCall }}

    rule VariableReference:
          r'\$' QName
          {{ return X.VariableReference(*QName) }}

    rule ContextItemExpr:
          r'\.'                         {{ return X.AxisStep('self') }}

    rule FunctionCall:
          FUNCNAME r'\('                {{ args = [] }}
          [
            Expr                        {{ args.append(Expr) }}
            (
              r'\,' Expr                {{ args.append(Expr) }}
            )*
          ] r'\)'                   {{ return X.Function(FUNCNAME, args) }}

    rule KindTest:
          PITest                        {{ return PITest }}
        | CommentTest                   {{ return CommentTest }}
        | TextTest                      {{ return TextTest }}
        | AnyKindTest                   {{ return AnyKindTest }}

    rule PITest:
          r'processing-instruction'     {{ name = None }}
          r'\(' [
              NCNAME                    {{ name = NCNAME }}
            | StringLiteral             {{ name = StringLiteral }}
          ] r'\)'                       {{ return X.PITest(name) }}

    rule CommentTest:
          r'comment' r'\(' r'\)'        {{ return X.CommentTest() }}

    rule TextTest:
          r'text' r'\(' r'\)'           {{ return X.TextTest() }}

    rule AnyKindTest:
          r'node' r'\(' r'\)'           {{ return X.AnyKindTest() }}

    rule Literal:
          NumericLiteral                {{ return NumericLiteral }}
        | StringLiteral                 {{ return StringLiteral }}

    rule NumericLiteral:
          NUMBER                        {{ return float(NUMBER) }}

    rule StringLiteral:
          DQUOTE                        {{ return DQUOTE[1:-1] }}
        | SQUOTE                        {{ return SQUOTE[1:-1] }}

    rule QName:
          NCNAME                        {{ name = NCNAME }}
          [
            r'\:' NCNAME                {{ return (name, NCNAME) }}
          ]                             {{ return (None, name) }}
