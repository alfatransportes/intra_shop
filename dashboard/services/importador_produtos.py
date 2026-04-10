from decimal import Decimal, InvalidOperation
from typing import Dict, Tuple

import pandas as pd
from django.db import transaction

from website.models import NivelAvaria, Produto, ProdutoVariacao, Tipo, Unidade

COLUNAS_PRODUTOS_OBRIGATORIAS = {
    "nome",
    "unidade_prod",
    "tipo_prod",
    "nivel_ava_prod",
    "usa_variacoes",
    "quantidade",
    "maximo_por_usuario",
    "valor_nota",
    "porcen_desconto",
    "descricao",
    "ativo",
}

COLUNAS_VARIACOES_OBRIGATORIAS = {
    "produto_ref",
    "categoria",
    "genero",
    "faixa_etaria",
    "tamanho",
    "cor",
    "quantidade",
    "ativo",
}


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(col).strip().lower() for col in df.columns]
    return df


def parse_int(valor, default=0):
    if pd.isna(valor) or str(valor).strip() == "":
        return default
    try:
        return int(float(str(valor).replace(",", ".")))
    except Exception:
        raise ValueError(f"Valor inteiro inválido: {valor}")


def parse_decimal(valor, default=Decimal("0.00")):
    if pd.isna(valor) or str(valor).strip() == "":
        return default
    try:
        texto = str(valor).strip().replace(".", "").replace(",", ".")
        # se já veio com ponto decimal padrão, corrige o excesso
        if texto.count(".") > 1:
            partes = texto.split(".")
            texto = "".join(partes[:-1]) + "." + partes[-1]
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Valor decimal inválido: {valor}")


def parse_bool(valor, default=False):
    if pd.isna(valor) or str(valor).strip() == "":
        return default

    texto = str(valor).strip().lower()
    if texto in {"1", "true", "sim", "s", "yes", "y"}:
        return True
    if texto in {"0", "false", "nao", "não", "n", "no"}:
        return False

    raise ValueError(f"Valor booleano inválido: {valor}")


def parse_unidade(valor):
    valor = normalizar_texto(valor)
    if not valor:
        raise ValueError("Unidade não informada.")

    if " - " in valor:
        codigo_txt, nome = valor.split(" - ", 1)
        codigo_txt = codigo_txt.strip()
        nome = nome.strip()

        if codigo_txt.isdigit():
            codigo = int(codigo_txt)
            unidade = Unidade.objects.filter(codigo=codigo, nome=nome).first()
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
    valor = normalizar_texto(valor)
    if not valor:
        raise ValueError("Tipo não informado.")

    tipo = Tipo.objects.filter(nome=valor).first()
    if tipo:
        return tipo

    raise ValueError(f"Tipo inválido: {valor}")


def parse_nivel_avaria(valor):
    valor = normalizar_texto(valor)
    if not valor:
        raise ValueError("Nível de avaria não informado.")

    nivel = NivelAvaria.objects.filter(nome=valor).first()
    if nivel:
        return nivel

    raise ValueError(f"Nível de avaria inválido: {valor}")


def parse_choice_field(model_class, field_name, valor):
    valor = normalizar_texto(valor)
    if not valor:
        return None

    field = model_class._meta.get_field(field_name)
    choices = dict(field.choices or [])

    # aceita tanto o value quanto o label
    for choice_value, choice_label in choices.items():
        if valor == str(choice_value):
            return choice_value
        if valor.lower() == str(choice_label).strip().lower():
            return choice_value

    raise ValueError(f"Valor inválido para {field_name}: {valor}")


def ler_arquivo_importacao(arquivo) -> Dict[str, pd.DataFrame]:
    nome = arquivo.name.lower()

    if nome.endswith(".csv"):
        try:
            df = pd.read_csv(arquivo, sep=None, engine="python")
        except Exception:
            arquivo.seek(0)
            df = pd.read_csv(arquivo, sep=";")
        return {"IMPORTACAO_PRODUTOS": normalizar_colunas(df)}

    if nome.endswith(".xlsx"):
        planilhas = pd.read_excel(arquivo, sheet_name=None, engine="openpyxl")
        return {str(nome_aba).strip(): normalizar_colunas(df) for nome_aba, df in planilhas.items()}

    if nome.endswith(".xls"):
        planilhas = pd.read_excel(arquivo, sheet_name=None)
        return {str(nome_aba).strip(): normalizar_colunas(df) for nome_aba, df in planilhas.items()}

    raise ValueError("Formato não suportado. Envie um arquivo CSV, XLS ou XLSX.")


def get_sheet(planilhas, nome_aba):
    for chave, df in planilhas.items():
        if chave.strip().upper() == nome_aba.strip().upper():
            return df
    return None


def localizar_produto_por_referencia(produtos_importados: Dict[str, Produto], referencia: str) -> Produto:
    referencia = normalizar_texto(referencia)
    if not referencia:
        raise ValueError("produto_ref não informado.")

    if referencia in produtos_importados:
        return produtos_importados[referencia]

    produto = Produto.objects.filter(num_controle=referencia).first()
    if produto:
        return produto

    produto = Produto.objects.filter(nome=referencia).first()
    if produto:
        return produto

    raise ValueError(f"Produto de referência não encontrado: {referencia}")


@transaction.atomic
def importar_produtos(arquivo):
    planilhas = ler_arquivo_importacao(arquivo)

    df_produtos = get_sheet(planilhas, "IMPORTACAO_PRODUTOS")
    if df_produtos is None:
        raise ValueError("A aba IMPORTACAO_PRODUTOS é obrigatória.")

    faltando_produtos = COLUNAS_PRODUTOS_OBRIGATORIAS - set(df_produtos.columns)
    if faltando_produtos:
        raise ValueError(
            "Colunas obrigatórias ausentes em IMPORTACAO_PRODUTOS: "
            + ", ".join(sorted(faltando_produtos))
        )

    df_variacoes = get_sheet(planilhas, "IMPORTACAO_VARIACOES")
    if df_variacoes is not None and not df_variacoes.empty:
        faltando_variacoes = COLUNAS_VARIACOES_OBRIGATORIAS - set(df_variacoes.columns)
        if faltando_variacoes:
            raise ValueError(
                "Colunas obrigatórias ausentes em IMPORTACAO_VARIACOES: "
                + ", ".join(sorted(faltando_variacoes))
            )

    resultado = {
        "criados": 0,
        "atualizados": 0,
        "variacoes_criadas": 0,
        "variacoes_atualizadas": 0,
        "erros": [],
    }

    produtos_importados: Dict[str, Produto] = {}
    ativacao_solicitada: Dict[int, bool] = {}

    # 1) produtos
    for index, row in df_produtos.iterrows():
        linha = index + 2

        try:
            nome = normalizar_texto(row["nome"])
            if not nome:
                raise ValueError("Nome do produto não informado.")

            unidade = parse_unidade(row["unidade_prod"])
            tipo = parse_tipo(row["tipo_prod"])
            nivel = parse_nivel_avaria(row["nivel_ava_prod"])

            num_controle = normalizar_texto(row.get("num_controle"))
            usa_variacoes = parse_bool(row["usa_variacoes"], default=False)
            ativo = parse_bool(row["ativo"], default=False)

            quantidade = parse_int(row["quantidade"], default=0)
            if usa_variacoes:
                quantidade = 0

            descricao = normalizar_texto(row["descricao"])

            defaults = {
                "nome": nome,
                "num_controle": num_controle or None,
                "unidade_prod": unidade,
                "tipo_prod": tipo,
                "nivel_ava_prod": nivel,
                "usa_variacoes": usa_variacoes,
                "quantidade": quantidade,
                "maximo_por_usuario": parse_int(row["maximo_por_usuario"], default=0),
                "valor_nota": parse_decimal(row["valor_nota"]),
                "porcen_desconto": parse_decimal(row["porcen_desconto"]),
                "descricao": descricao,
                # salva inicialmente como False e tenta publicar no final
                "ativo": False,
            }

            if num_controle:
                produto, criado = Produto.objects.update_or_create(
                    num_controle=num_controle,
                    defaults=defaults,
                )
            else:
                produto, criado = Produto.objects.update_or_create(
                    nome=nome,
                    defaults=defaults,
                )

            produto.save()

            referencia = num_controle or nome
            produtos_importados[referencia] = produto
            ativacao_solicitada[produto.pk] = ativo

            if criado:
                resultado["criados"] += 1
            else:
                resultado["atualizados"] += 1

        except Exception as e:
            resultado["erros"].append(f"[PRODUTOS] Linha {linha}: {e}")

    # 2) variações
    if df_variacoes is not None and not df_variacoes.empty:
        for index, row in df_variacoes.iterrows():
            linha = index + 2

            try:
                produto_ref = normalizar_texto(row["produto_ref"])
                produto = localizar_produto_por_referencia(produtos_importados, produto_ref)

                if not produto.usa_variacoes:
                    raise ValueError(
                        f"O produto '{produto.nome}' não está marcado como usa_variacoes."
                    )

                categoria = parse_choice_field(ProdutoVariacao, "categoria", row["categoria"])
                genero = parse_choice_field(ProdutoVariacao, "genero", row["genero"])
                faixa_etaria = parse_choice_field(ProdutoVariacao, "faixa_etaria", row["faixa_etaria"])
                tamanho = normalizar_texto(row["tamanho"]) or None
                cor = normalizar_texto(row["cor"]) or None
                quantidade = parse_int(row["quantidade"], default=0)
                ativo = parse_bool(row["ativo"], default=True)

                defaults = {
                    "quantidade": quantidade,
                    "ativo": ativo,
                }

                variacao, criada = ProdutoVariacao.objects.update_or_create(
                    produto=produto,
                    categoria=categoria,
                    genero=genero,
                    faixa_etaria=faixa_etaria,
                    tamanho=tamanho,
                    cor=cor,
                    defaults=defaults,
                )

                if criada:
                    resultado["variacoes_criadas"] += 1
                else:
                    resultado["variacoes_atualizadas"] += 1

            except Exception as e:
                resultado["erros"].append(f"[VARIACOES] Linha {linha}: {e}")

    # 3) tentativa final de publicação
    for produto_id, ativo_solicitado in ativacao_solicitada.items():
        produto = Produto.objects.filter(pk=produto_id).first()
        if not produto:
            continue

        if not ativo_solicitado:
            if produto.ativo:
                produto.ativo = False
                produto.save(update_fields=["ativo"])
            continue

        pode_publicar = False
        motivo = ""

        if hasattr(produto, "pode_ativar"):
            try:
                pode_publicar, motivo = produto.pode_ativar()
            except Exception:
                pode_publicar = False
                motivo = "Falha ao validar publicação."
        else:
            # fallback para versões antigas do model
            if produto.usa_variacoes:
                tem_variacao = produto.variacoes.filter(ativo=True, quantidade__gt=0).exists()
                pode_publicar = bool(produto.imagens.exists() and tem_variacao)
                if not pode_publicar:
                    motivo = "Produto com variações precisa de imagem e variação ativa com estoque."
            else:
                pode_publicar = bool(produto.imagens.exists() and (produto.quantidade or 0) > 0)
                if not pode_publicar:
                    motivo = "Produto simples precisa de imagem e quantidade maior que zero."

        if pode_publicar:
            if not produto.ativo:
                produto.ativo = True
                produto.save(update_fields=["ativo"])
        else:
            if produto.ativo:
                produto.ativo = False
                produto.save(update_fields=["ativo"])
            resultado["erros"].append(
                f"[PUBLICACAO] Produto '{produto.nome}' ficou como rascunho. Motivo: {motivo or 'requisitos não atendidos.'}"
            )

    return resultado