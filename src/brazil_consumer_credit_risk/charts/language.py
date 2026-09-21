"""Everything the charts and the write-up say, in Portuguese and English.

The Portuguese is the reference version; the English is a translation of it. Keeping both in one
file, key by key, is what stops them drifting apart. Headlines are chosen once, from the data, by
the rules in `headlines`; a Language only words the result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .style import INCOME_BANDS as _BANDS


@dataclass(frozen=True)
class Language:
    code: str
    decimal: str
    thousands: str
    pp_unit: str
    and_word: str
    months: tuple[str, ...]
    counts: dict[int, str]
    feminine_counts: dict[int, str]
    labels: dict[str, dict[str, str]]
    text: dict[str, str] = field(repr=False)

    def number(self, x: float, decimals: int = 2, sign: bool = False) -> str:
        """A number with this language's separators and a true minus sign."""
        raw = f"{abs(x):,.{decimals}f}"
        text = raw.replace(",", "_").replace(".", self.decimal).replace("_", self.thousands)
        if x < 0 and float(f"{abs(x):.{decimals}f}") != 0:
            return "−" + text
        return ("+" + text) if sign else text

    def pp(self, rate: float, decimals: int = 2, sign: bool = False) -> str:
        """A rate difference, stored as a fraction, in percentage points."""
        return f"{self.number(100 * rate, decimals, sign)} {self.pp_unit}"

    def pct(self, rate: float, decimals: int = 1, sign: bool = False) -> str:
        """A rate or growth, stored as a fraction, as a percentage."""
        return f"{self.number(100 * rate, decimals, sign)}%"

    def month(self, month: date) -> str:
        name = self.months[month.month - 1]
        return f"{name}/{month.year}" if self.code == "pt" else f"{name} {month.year}"

    def month_range(self, start: date, end: date) -> str:
        """Two months of the same year: mar–dez/2019, Mar–Dec 2019."""
        return f"{self.months[start.month - 1]}–{self.month(end)}"

    def count(self, n: int, feminine: bool = False) -> str:
        """Counts up to ten spelled out, as prose expects."""
        if feminine and n in self.feminine_counts:
            return self.feminine_counts[n]
        return self.counts.get(n, str(n))

    def join(self, items) -> str:
        items = list(items)
        if len(items) == 1:
            return items[0]
        return ", ".join(items[:-1]) + f" {self.and_word} " + items[-1]

    def label(self, kind: str, key: str) -> str:
        return self.labels[kind][key]

    def t(self, key: str, **values) -> str:
        return self.text[key].format(**values)


PT = Language(
    code="pt",
    decimal=",",
    thousands=".",
    pp_unit="p.p.",
    and_word="e",
    months=("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"),
    counts={
        1: "um",
        2: "dois",
        3: "três",
        4: "quatro",
        5: "cinco",
        6: "seis",
        7: "sete",
        8: "oito",
        9: "nove",
        10: "dez",
    },
    feminine_counts={1: "uma", 2: "duas"},
    labels={
        "occupation": {
            "Aposentado/pensionista": "Aposentados e pensionistas",
            "Autônomo": "Autônomos",
            "Empregado de empresa privada": "Empregados do setor privado",
            "Servidor ou empregado público": "Servidores e empregados públicos",
            "Empresário": "Empresários",
            "MEI": "MEI",
            "Empregado de entidades sem fins lucrativos": (
                "Empregados de entidades\nsem fins lucrativos"
            ),
            "Outros": "Outros",
        },
        "occupation_in_text": {
            "Aposentado/pensionista": "aposentados e pensionistas",
            "Autônomo": "autônomos",
            "Empregado de empresa privada": "empregados do setor privado",
            "Servidor ou empregado público": "servidores e empregados públicos",
            "Empresário": "empresários",
            "MEI": "MEI",
            "Empregado de entidades sem fins lucrativos": (
                "empregados de entidades sem fins lucrativos"
            ),
            "Outros": "outros",
        },
        "band": dict(
            zip(
                _BANDS,
                ["Até 1", "1 a 2", "2 a 3", "3 a 5", "5 a 10", "10 a 20", "Acima de 20"],
                strict=True,
            )
        ),
        "band_in_text": dict(
            zip(
                _BANDS,
                [
                    "até 1 salário mínimo",
                    "de 1 a 2 salários mínimos",
                    "de 2 a 3 salários mínimos",
                    "de 3 a 5 salários mínimos",
                    "de 5 a 10 salários mínimos",
                    "de 10 a 20 salários mínimos",
                    "acima de 20 salários mínimos",
                ],
                strict=True,
            )
        ),
        "pair_a": {
            "retiree_vs_self_employed": "aposentados",
            "public_vs_private_employee": "servidores públicos",
            "mei_vs_business_owner": "MEI",
        },
        "pair_b": {
            "retiree_vs_self_employed": "autônomos",
            "public_vs_private_employee": "empregados do setor privado",
            "mei_vs_business_owner": "empresários",
        },
        "pair_title": {
            "retiree_vs_self_employed": "Aposentados − autônomos",
            "public_vs_private_employee": "Servidores − empregados privados",
            "mei_vs_business_owner": "MEI − empresários",
        },
        "product_in_text": {
            "Cartão": "cartão de crédito",
            "Consignado": "consignado",
            "Imobiliário": "crédito imobiliário",
            "Pessoal não consignado": "crédito pessoal sem consignação",
            "Veículos": "financiamento de veículos",
            "Rural": "crédito rural",
            "Cheque especial e outros": "cheque especial e outros",
        },
        "component": {
            "pure_rate": "dentro de cada ocupação e produto",
            "product_mix": "da mudança no mix de produtos",
            "borrower_mix": "da mudança no mix de ocupações",
        },
    },
    text={
        "source": "Elaboração própria com dados do Banco Central do Brasil (SCR.data e SGS, "
        "licença ODbL). Pessoas físicas.",
        "as_of": "Dados até {month}.",
        # the write-up (report.py)
        "report.trillion": "R$ {value} trilhões",
        "report.billion": "R$ {value} bi",
        "report.bands": "{bands} salários mínimos",
        # chart 1
        "trap.title.hidden": "A mudança contábil de janeiro de 2025 não aparece como salto na "
        "inadimplência de 90 dias das famílias",
        "trap.title.flat": "Parte da alta da inadimplência das famílias desde janeiro de 2025 vem "
        "de uma mudança contábil, não dos devedores; a de 15 a 90 dias não saltou",
        "trap.title.jumped": "Parte da alta da inadimplência das famílias desde janeiro de 2025 "
        "vem de uma mudança contábil, e até a de 15 a 90 dias saltou naquele mês",
        "trap.subtitle": "Inadimplência das pessoas físicas, % da carteira. De dezembro de 2024 "
        "para janeiro de 2025, a de 90 dias variou {d90} (no janeiro anterior, {d90_before}) e a "
        "de 15 a 90 dias, {d15} ({d15_before}).",
        "trap.official": "Série oficial do BCB (SGS 21084)",
        "trap.d90": "90 dias, SCR.data",
        "trap.d90_after": "90 dias, não comparável após dez/2024",
        "trap.rule": "Res. CMN 4.966\njan/2025",
        "trap.bcb": "O BCB estima que {regulatory} dos {total} p.p. de alta\nda inadimplência de "
        "90 dias do sistema\nfinanceiro em jan–jun/2025 vieram da nova regra",
        "trap.ylabel": "% da carteira",
        "d90": "90 dias",
        "d15": "15 a 90 dias",
        # chart 2
        "grid.title.flat": "Dentro de uma mesma faixa de renda, a ocupação quase não muda a "
        "inadimplência",
        "grid.subtitle.flat": "Inadimplência de 90 dias em {period}, por ocupação e faixa de "
        "renda, % da carteira. Em nenhuma faixa a diferença entre ocupações chega a {material} "
        "com a ordem mantida pelo denominador defasado.",
        "grid.title": "Na mesma faixa de renda, a inadimplência de 90 dias varia até {spread} "
        "conforme a ocupação",
        "grid.subtitle": "Inadimplência de 90 dias em {period}, por ocupação e faixa de renda, % "
        "da carteira. A maior diferença é entre {high} e {low} com renda {band}. Mesmo na faixa em "
        "que as ocupações ficam mais próximas, a diferença é de {smallest}.",
        "grid.balance": "R$ {bn} bi",
        "grid.note": " Células abaixo de R$ {min_cell} bi de saldo médio não são mostradas. "
        "Contornos: a maior diferença numa faixa.",
        "income_axis": "Renda mensal, em salários mínimos",
        # chart 3
        "dispersion.title.income": "Na inadimplência de 90 dias, a renda separa o risco mais do "
        "que a ocupação",
        "dispersion.title.occupation": "Na inadimplência de 90 dias, a ocupação separa o risco "
        "mais do que a renda",
        "dispersion.title.mixed": "Na inadimplência de 90 dias, nem a ocupação nem a renda separa "
        "sempre mais o risco",
        "dispersion.with": ", e a distância entre ocupações acompanhou o desemprego",
        "dispersion.against": ", e a distância entre ocupações andou na contramão do desemprego",
        "dispersion.neither": ", e a distância entre ocupações não acompanhou o desemprego",
        "dispersion.subtitle": "Dispersão da inadimplência de 90 dias entre ocupações, dentro de "
        "cada faixa de renda, dividida pela dispersão entre faixas, dentro de cada ocupação: "
        "abaixo de 1, a renda separa mais. Nos recortes do teste ({windows}), a razão foi "
        "{ratios}. Correlação da dispersão entre ocupações com o desemprego, {first} a {last}: "
        "{correlation} ({years} anos).",
        "dispersion.d15": " Na inadimplência de 15 a 90 dias, a razão passa de 1 em {years}.",
        "dispersion.windows": "Recortes do teste (90 dias)",
        "dispersion.above": "Acima de 1: a ocupação separa mais",
        "dispersion.below": "Abaixo de 1: a renda separa mais",
        "dispersion.ylabel": "Ocupação ÷ renda",
        "dispersion.unemployment": "Desemprego",
        "dispersion.note": " Ocupações e faixas nomeadas, células acima de R$ {min_cell} bi. "
        "Desemprego: média anual da PNAD Contínua (SGS 24369).",
        # chart 4
        "split.title.unstable": "Para {a} e {b}, a divisão entre ocupação e produto não é estável "
        "o bastante para uma conclusão",
        "split.title.most": "A maior parte da diferença entre {a} e {b} vem dos produtos de "
        "crédito de cada grupo",
        "split.title.less": "Menos da metade da diferença entre {a} e {b} vem dos produtos de "
        "crédito de cada grupo",
        "split.title.little": "Pouco da diferença entre {a} e {b} vem dos produtos de crédito de "
        "cada grupo: ela aparece dentro dos mesmos produtos",
        "split.subtitle": "Diferença na inadimplência de 90 dias em {period} entre {a} e {b}, por "
        "faixa de renda, dividida entre a parte dentro dos mesmos produtos e a parte que vem do "
        "mix de produtos.",
        "split.where.one": "Na única faixa em que a divisão é estável",
        "split.where.many": "Nas {n} faixas em que a divisão é estável",
        "split.share": " {where}, {lower} têm a menor taxa, e o mix de produtos responde por "
        "{share} da diferença",
        "split.rural": "; sem o crédito rural, por {share}.",
        "split.small": "abaixo do tamanho mínimo",
        "split.xlabel": "Diferença na inadimplência de 90 dias, p.p.",
        "split.within": "Dentro dos mesmos produtos",
        "split.mix": "Mix de produtos",
        "split.total": "Diferença total",
        "split.without_rural": "Diferença sem crédito rural",
        "split.unstable": "Divisão instável com outro agrupamento de produtos",
        "split.unreadable": "Diferença abaixo de {material} ou ordem que muda com a defasagem",
        "split.note": " Divisão estável: diferença de ao menos {material}, mesma ordem com o "
        "denominador de 12 meses antes e parte do mix que muda menos de {shift} da diferença "
        "quando produtos ambíguos trocam de grupo.",
        # chart 5
        "mix.title.shared": "Em cada um dos {n} episódios de {first} a {last}, a inadimplência de "
        "90 dias das famílias mudou sobretudo {component}",
        "mix.title.biggest": "A {direction} de {size} na inadimplência de 90 dias das famílias em "
        "{episode} ",
        "mix.came": "veio sobretudo {component}",
        "mix.no_source": "não teve uma fonte dominante",
        "mix.rise": "alta",
        "mix.fall": "queda",
        "mix.subtitle": "Variação da inadimplência de 90 dias das pessoas físicas em cada "
        "episódio, dividida em três partes que somam exatamente a variação: taxa dentro de cada "
        "ocupação e produto, mix de produtos e mix de ocupações. Variação total: {changes}.",
        "mix.flagged": " {episodes}: há uma reclassificação de ocupações dentro do episódio, e ela "
        "entra no mix de ocupações.",
        "mix.pure_rate": "Taxa dentro de cada ocupação e produto",
        "mix.product_mix": "Mix de produtos",
        "mix.borrower_mix": "Mix de ocupações",
        "mix.total": "Variação total",
        "mix.note": " Episódios de janeiro a dezembro; a taxa de 90 dias é comparável até "
        "dez/2024.",
        # chart 6
        "current.base": "Variação da inadimplência de 15 a 90 dias entre 2024 e os 12 meses até "
        "{latest}, por ocupação, ao lado da variação real do saldo (IPCA).",
        "current.title.even": "Desde a mudança contábil, a inadimplência de 15 a 90 dias subiu de "
        "forma parecida em todas as ocupações",
        "current.title.depends": "Desde a mudança contábil, a inadimplência de 15 a 90 dias subiu "
        "de forma desigual, mas qual ocupação subiu mais depende do denominador",
        "current.title.fastest": "Desde a mudança contábil, a inadimplência de 15 a 90 dias subiu "
        "mais entre {who}, e o crédito a eles {growth} em termos reais",
        "current.grew": "continuou crescendo",
        "current.shrank": "encolheu",
        "current.detail": " Entre {who}: {change} na taxa e {growth} no saldo; entre as "
        "ocupações, a alta vai de {low} a {high}.",
        "current.tightening": " Taxa e saldo em queda juntos ({who}) sugerem crédito mais "
        "restrito, não devedores melhores.",
        "current.lagged": "Com denominador defasado (3 meses)",
        "current.rate_title": "Inadimplência de 15 a 90 dias, variação em p.p.",
        "current.balance_title": "Saldo real, variação em %",
        "current.note": " Desde 2025, valores vencidos incluem juros contratuais até o ativo ser "
        "problemático, o que pode elevar um pouco os saldos com 60 a 90 dias de atraso.",
    },
)

EN = Language(
    code="en",
    decimal=".",
    thousands=",",
    pp_unit="pp",
    and_word="and",
    months=("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    counts={
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
        9: "nine",
        10: "ten",
    },
    feminine_counts={},
    labels={
        "occupation": {
            "Aposentado/pensionista": "Retirees and pensioners",
            "Autônomo": "Self-employed",
            "Empregado de empresa privada": "Private-sector employees",
            "Servidor ou empregado público": "Public-sector employees",
            "Empresário": "Business owners",
            "MEI": "Micro-entrepreneurs (MEI)",
            "Empregado de entidades sem fins lucrativos": "Non-profit employees",
            "Outros": "Other",
        },
        "occupation_in_text": {
            "Aposentado/pensionista": "retirees and pensioners",
            "Autônomo": "the self-employed",
            "Empregado de empresa privada": "private-sector employees",
            "Servidor ou empregado público": "public-sector employees",
            "Empresário": "business owners",
            "MEI": "micro-entrepreneurs (MEI)",
            "Empregado de entidades sem fins lucrativos": "non-profit employees",
            "Outros": "other occupations",
        },
        "band": dict(
            zip(
                _BANDS,
                ["Up to 1", "1 to 2", "2 to 3", "3 to 5", "5 to 10", "10 to 20", "Above 20"],
                strict=True,
            )
        ),
        "band_in_text": dict(
            zip(
                _BANDS,
                [
                    "up to 1 minimum wage",
                    "1 to 2 minimum wages",
                    "2 to 3 minimum wages",
                    "3 to 5 minimum wages",
                    "5 to 10 minimum wages",
                    "10 to 20 minimum wages",
                    "above 20 minimum wages",
                ],
                strict=True,
            )
        ),
        "pair_a": {
            "retiree_vs_self_employed": "retirees",
            "public_vs_private_employee": "public-sector employees",
            "mei_vs_business_owner": "micro-entrepreneurs (MEI)",
        },
        "pair_b": {
            "retiree_vs_self_employed": "the self-employed",
            "public_vs_private_employee": "private-sector employees",
            "mei_vs_business_owner": "business owners",
        },
        "pair_title": {
            "retiree_vs_self_employed": "Retirees − self-employed",
            "public_vs_private_employee": "Public − private-sector employees",
            "mei_vs_business_owner": "MEI − business owners",
        },
        "product_in_text": {
            "Cartão": "credit cards",
            "Consignado": "payroll-deducted loans",
            "Imobiliário": "mortgages",
            "Pessoal não consignado": "unsecured personal loans",
            "Veículos": "vehicle finance",
            "Rural": "rural credit",
            "Cheque especial e outros": "overdrafts and other credit",
        },
        "component": {
            "pure_rate": "within each occupation and product",
            "product_mix": "through a shift in the product mix",
            "borrower_mix": "through a shift in the occupation mix",
        },
    },
    text={
        "source": "Author's calculations from Banco Central do Brasil data (SCR.data and SGS, "
        "ODbL licence). Households.",
        "as_of": "Data to {month}.",
        # the write-up (report.py)
        "report.trillion": "R${value} trillion",
        "report.billion": "R${value} billion",
        "report.bands": "{bands} minimum wages",
        # chart 1
        "trap.title.hidden": "The January 2025 accounting change doesn't show as a jump in "
        "household 90-day delinquency",
        "trap.title.flat": "Part of the rise in household delinquency since January 2025 is an "
        "accounting change, not borrowers; 15–90-day delinquency didn't jump",
        "trap.title.jumped": "Part of the rise in household delinquency since January 2025 is an "
        "accounting change, and even 15–90-day delinquency jumped that month",
        "trap.subtitle": "Household delinquency, % of the portfolio. From December 2024 to "
        "January 2025, the 90-day rate moved {d90} (the January before, {d90_before}) and the "
        "15–90-day rate {d15} ({d15_before}).",
        "trap.official": "BCB official series (SGS 21084)",
        "trap.d90": "90-day, SCR.data",
        "trap.d90_after": "90-day, not comparable after Dec 2024",
        "trap.rule": "Res. CMN 4.966\nJan 2025",
        "trap.bcb": "The BCB estimates that {regulatory} of the {total} pp rise\nin 90-day "
        "delinquency across the financial\nsystem in Jan–Jun 2025 came from the new rule",
        "trap.ylabel": "% of the portfolio",
        "d90": "90-day",
        "d15": "15–90-day",
        # chart 2
        "grid.title.flat": "Within an income band, occupation barely changes delinquency",
        "grid.subtitle.flat": "90-day delinquency in {period}, by occupation and income band, % of "
        "the portfolio. In no band does the gap between occupations reach {material} with its "
        "order holding under the lagged denominator.",
        "grid.title": "At the same income, 90-day delinquency varies by up to {spread} with "
        "occupation",
        "grid.subtitle": "90-day delinquency in {period}, by occupation and income band, % of the "
        "portfolio. The largest gap is between {high} and {low} earning {band}. Even in the band "
        "where occupations sit closest, the gap is {smallest}.",
        "grid.balance": "R${bn} bn",
        "grid.note": " Cells under R${min_cell} bn of average balance are not shown. Outlines: the "
        "largest gap within a band.",
        "income_axis": "Monthly income, in minimum wages",
        # chart 3
        "dispersion.title.income": "On 90-day delinquency, income separates risk more than "
        "occupation does",
        "dispersion.title.occupation": "On 90-day delinquency, occupation separates risk more than "
        "income does",
        "dispersion.title.mixed": "On 90-day delinquency, neither occupation nor income "
        "consistently separates risk more",
        "dispersion.with": ", and the gap between occupations tracked unemployment",
        "dispersion.against": ", and the gap between occupations moved against unemployment",
        "dispersion.neither": ", and the gap between occupations didn't track unemployment",
        "dispersion.subtitle": "Spread of 90-day delinquency across occupations within each income "
        "band, divided by the spread across bands within each occupation: below 1, income "
        "separates more. In the test windows ({windows}), the ratio was {ratios}. Correlation of "
        "the occupation spread with unemployment, {first} to {last}: {correlation} ({years} "
        "years).",
        "dispersion.d15": " On 15–90-day delinquency, the ratio exceeds 1 in {years}.",
        "dispersion.windows": "Test windows (90-day)",
        "dispersion.above": "Above 1: occupation separates more",
        "dispersion.below": "Below 1: income separates more",
        "dispersion.ylabel": "Occupation ÷ income",
        "dispersion.unemployment": "Unemployment",
        "dispersion.note": " Named occupations and bands, cells above R${min_cell} bn. "
        "Unemployment: annual average, PNAD Contínua (SGS 24369).",
        # chart 4
        "split.title.unstable": "For {a} and {b}, the split between occupation and product isn't "
        "stable enough to conclude",
        "split.title.most": "Most of the gap between {a} and {b} comes from the credit products "
        "each group holds",
        "split.title.less": "Less than half of the gap between {a} and {b} comes from the credit "
        "products each group holds",
        "split.title.little": "Little of the gap between {a} and {b} comes from the credit "
        "products each group holds: it shows up within the same products",
        "split.subtitle": "Gap in 90-day delinquency in {period} between {a} and {b}, by income "
        "band, split into the part within the same products and the part from the product mix.",
        "split.where.one": "In the only band where the split is stable",
        "split.where.many": "In the {n} bands where the split is stable",
        "split.share": " {where}, {lower} have the lower rate, and the product mix accounts for "
        "{share} of the gap",
        "split.rural": "; without rural credit, {share}.",
        "split.small": "below the minimum size",
        "split.xlabel": "Gap in 90-day delinquency, pp",
        "split.within": "Within the same products",
        "split.mix": "Product mix",
        "split.total": "Total gap",
        "split.without_rural": "Gap without rural credit",
        "split.unstable": "Split unstable under another product grouping",
        "split.unreadable": "Gap under {material}, or an order that flips with the lag",
        "split.note": " Stable split: a gap of at least {material}, the same order with the "
        "denominator from 12 months earlier, and a product-mix part that moves by less than "
        "{shift} of the gap when ambiguous products change group.",
        # chart 5
        "mix.title.shared": "In each of the {n} episodes from {first} to {last}, household 90-day "
        "delinquency moved mostly {component}",
        "mix.title.biggest": "The {direction} of {size} in household 90-day delinquency in "
        "{episode} ",
        "mix.came": "came mostly {component}",
        "mix.no_source": "had no dominant source",
        "mix.rise": "rise",
        "mix.fall": "fall",
        "mix.subtitle": "Change in household 90-day delinquency in each episode, split into three "
        "parts that add up exactly to the change: the rate within each occupation and product, "
        "the product mix and the occupation mix. Total change: {changes}.",
        "mix.flagged": " {episodes}: an occupation reclassification falls inside the episode and "
        "enters the occupation mix.",
        "mix.pure_rate": "Rate within each occupation and product",
        "mix.product_mix": "Product mix",
        "mix.borrower_mix": "Occupation mix",
        "mix.total": "Total change",
        "mix.note": " Episodes run January to December; the 90-day rate is comparable to Dec 2024.",
        # chart 6
        "current.base": "Change in 15–90-day delinquency between 2024 and the 12 months to "
        "{latest}, by occupation, next to the real change in balances (IPCA).",
        "current.title.even": "Since the accounting change, 15–90-day delinquency has risen about "
        "evenly across occupations",
        "current.title.depends": "Since the accounting change, 15–90-day delinquency has risen "
        "unevenly, but which occupation rose most depends on the denominator",
        "current.title.fastest": "Since the accounting change, 15–90-day delinquency has risen "
        "most among {who}, and lending to them has {growth} in real terms",
        "current.grew": "kept growing",
        "current.shrank": "shrunk",
        "current.detail": " Among {who}: {change} in the rate and {growth} in balances; across "
        "occupations, the rise runs from {low} to {high}.",
        "current.tightening": " A falling rate with a shrinking balance ({who}) suggests tighter "
        "lending, not better borrowers.",
        "current.lagged": "With lagged denominator (3 months)",
        "current.rate_title": "15–90-day delinquency, change in pp",
        "current.balance_title": "Real balance, change in %",
        "current.note": " Since 2025, overdue amounts include contractual interest until an asset "
        "becomes a problem asset, which may slightly raise balances 60 to 90 days overdue.",
    },
)

LANGUAGES = {"pt": PT, "en": EN}
