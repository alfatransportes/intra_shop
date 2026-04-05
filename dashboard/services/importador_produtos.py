from decimal import Decimal, InvalidOperation

import pandas as pd
from django.db import transaction

from website.models import NivelAvaria, Produto, Tipo, Unidade

COLUNAS_OBRIGATORIAS = {
    "nome",
    "unidade_prod",
    "tipo_prod",
    "nivel_ava_prod",
    "quantidade",
    "maximo_por_usuario",
    "valor_nota",
    "porcen_desconto",
    "descricao",
    "ativo",
}


def normalizar_colunas(df):
    mapeamento = {
        "unidade": "unidade_prod",
        "tipo": "tipo_prod",
        "nivel_avaria": "nivel_ava_prod",
    }

    df.columns = [
        mapeamento.get(
            str(col).strip().lower().replace(" ", "_"),
            str(col).strip().lower().replace(" ", "_"),
        )
        for col in df.columns
    ]
    return df


def parse_bool(valor):
    if pd.isna(valor):
        return False
    valor = str(valor).strip().lower()
    return valor in {"1", "true", "sim", "s", "yes", "y"}


def parse_int(valor, default=0):
    if pd.isna(valor) or valor == "":
        return default
    try:
        return int(float(valor))
    except Exception:
        raise ValueError(f"Valor inteiro inválido: {valor}")


def parse_decimal(valor, default="0.00"):
    if pd.isna(valor) or valor == "":
        return Decimal(default)

    if isinstance(valor, (int, float)):
        return Decimal(str(valor)).quantize(Decimal("0.01"))

    texto = str(valor).strip()

    try:
        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", ".")
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Valor decimal inválido: {valor}")


def parse_unidade(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        raise ValueError("Unidade não informada.")

    valor = str(valor).strip()

    if " - " in valor:
        codigo_str, nome = valor.split(" - ", 1)

        try:
            codigo = int(codigo_str.strip())
        except ValueError:
            raise ValueError(f"Unidade inválida: {valor}")

        unidade = Unidade.objects.filter(
            codigo=codigo,
            nome=nome.strip(),
        ).first()
        if unidade:
            return unidade

        unidade = Unidade.objects.filter(codigo=codigo).first()
        if unidade:
            return unidade

    unidade = Unidade.objects.filter(nome=valor).first()
    if unidade:
        return unidade

    raise ValueError(f"Unidade inválida: {valor}")


def parse_tipo(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        raise ValueError("Tipo não informado.")

    valor = str(valor).strip()

    tipo = Tipo.objects.filter(nome=valor).first()
    if tipo:
        return tipo

    raise ValueError(f"Tipo inválido: {valor}")


def parse_nivel_avaria(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        raise ValueError("Nível de avaria não informado.")

    valor = str(valor).strip()

    nivel = NivelAvaria.objects.filter(nome=valor).first()
    if nivel:
        return nivel

    raise ValueError(f"Nível de avaria inválido: {valor}")


def ler_arquivo(arquivo):
    nome = arquivo.name.lower()

    if nome.endswith(".csv"):
        try:
            return pd.read_csv(arquivo, sep=None, engine="python")
        except Exception:
            arquivo.seek(0)
            return pd.read_csv(arquivo, sep=";")
    elif nome.endswith(".xlsx"):
        return pd.read_excel(arquivo, engine="openpyxl")
    elif nome.endswith(".xls"):
        return pd.read_excel(arquivo)
    else:
        raise ValueError("Formato não suportado. Envie um arquivo CSV, XLS ou XLSX.")


@transaction.atomic
def importar_produtos(arquivo):
    df = ler_arquivo(arquivo)
    df = normalizar_colunas(df)

    faltando = COLUNAS_OBRIGATORIAS - set(df.columns)
    if faltando:
        raise ValueError(
            "Colunas obrigatórias ausentes: " + ", ".join(sorted(faltando))
        )

    resultado = {
        "criados": 0,
        "atualizados": 0,
        "erros": [],
    }

    for index, row in df.iterrows():
        linha = index + 2  # cabeçalho = linha 1

        try:
            nome = str(row["nome"]).strip()
            if not nome:
                raise ValueError("Nome do produto não informado.")

            unidade = parse_unidade(row["unidade_prod"])
            tipo = parse_tipo(row["tipo_prod"])
            nivel = parse_nivel_avaria(row["nivel_ava_prod"])

            num_controle = None

            if not pd.isna(row.get("num_controle")):
                valor = str(row["num_controle"]).strip()
                if valor:
                    num_controle = valor

            descricao = ""
            if not pd.isna(row["descricao"]):
                descricao = str(row["descricao"]).strip()

            defaults = {
                "unidade_prod": unidade,
                "tipo_prod": tipo,
                "nivel_ava_prod": nivel,
                "quantidade": parse_int(row["quantidade"], default=1),
                "maximo_por_usuario": parse_int(row["maximo_por_usuario"], default=0),
                "valor_nota": parse_decimal(row["valor_nota"]),
                "porcen_desconto": parse_decimal(row["porcen_desconto"]),
                "descricao": descricao,
                "ativo": parse_bool(row["ativo"]),
            }

            if num_controle:
                produto, criado = Produto.objects.update_or_create(
                    num_controle=num_controle,
                    defaults={
                        "nome": nome,
                        "num_controle": num_controle,
                        **defaults
                    },
                )
            else:
                produto, criado = Produto.objects.update_or_create(
                    nome=nome,
                    defaults=defaults,
                )

            produto.save()

            if criado:
                resultado["criados"] += 1
            else:
                resultado["atualizados"] += 1

        except Exception as e:
            resultado["erros"].append(f"Linha {linha}: {e}")

    return resultado