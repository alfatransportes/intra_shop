# services/produto_import_service.py
from decimal import Decimal, InvalidOperation

import pandas as pd
from django.db import transaction

from website.models import NivelAvaria, Produto, Tipo, Unidade

COLUNAS_OBRIGATORIAS = {
    "nome",
    "unidade_codigo",
    "unidade_nome",
    "tipo",
    "nivel_avaria",
    "quantidade",
    "maximo_por_usuario",
    "valor_nota",
    "porcen_desconto",
    "descricao",
    "ativo",
}


def normalizar_colunas(df):
    df.columns = [
        str(col).strip().lower().replace(" ", "_")
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

    # Se já vier numérico do pandas/excel
    if isinstance(valor, (int, float)):
        return Decimal(str(valor)).quantize(Decimal("0.01"))

    texto = str(valor).strip()

    # tenta formato BR e EN
    try:
        if "," in texto and "." in texto:
            # 1.234,56 -> 1234.56
            texto = texto.replace(".", "").replace(",", ".")
        else:
            # 1234,56 -> 1234.56
            texto = texto.replace(",", ".")
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Valor decimal inválido: {valor}")


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

            unidade_codigo_raw = row["unidade_codigo"]
            unidade_codigo = None
            if not pd.isna(unidade_codigo_raw) and str(unidade_codigo_raw).strip() != "":
                unidade_codigo = parse_int(unidade_codigo_raw)

            unidade_nome = str(row["unidade_nome"]).strip()
            tipo_nome = str(row["tipo"]).strip()
            nivel_nome = str(row["nivel_avaria"]).strip()

            if not unidade_nome:
                raise ValueError("Unidade não informada.")
            if not tipo_nome:
                raise ValueError("Tipo não informado.")
            if not nivel_nome:
                raise ValueError("Nível de avaria não informado.")

            unidade, _ = Unidade.objects.get_or_create(
                codigo=unidade_codigo,
                nome=unidade_nome,
            )

            tipo, _ = Tipo.objects.get_or_create(
                nome=tipo_nome,
                defaults={"ativo": True},
            )

            nivel, _ = NivelAvaria.objects.get_or_create(
                nome=nivel_nome,
            )

            defaults = {
                "unidade_prod": unidade,
                "tipo_prod": tipo,
                "nivel_ava_prod": nivel,
                "quantidade": parse_int(row["quantidade"], default=1),
                "maximo_por_usuario": parse_int(row["maximo_por_usuario"], default=0),
                "valor_nota": parse_decimal(row["valor_nota"]),
                "porcen_desconto": parse_decimal(row["porcen_desconto"]),
                "descricao": str(row["descricao"]).strip(),
                "ativo": parse_bool(row["ativo"]),
            }

            produto, criado = Produto.objects.update_or_create(
                nome=nome,
                defaults=defaults,
            )

            # garante execução do save do model e recálculo de valor_venda
            produto.save()

            if criado:
                resultado["criados"] += 1
            else:
                resultado["atualizados"] += 1

        except Exception as e:
            resultado["erros"].append(f"Linha {linha}: {e}")

    return resultado