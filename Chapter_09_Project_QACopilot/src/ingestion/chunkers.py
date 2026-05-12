import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP, CODE_CHUNK_SIZE, CODE_CHUNK_OVERLAP


class CodeChunker:
    JAVA_SEPARATORS = [
        "\nclass ",
        "\npublic ",
        "\nprivate ",
        "\nprotected ",
        "\nvoid ",
        "\n@Test",
        "\n@Before",
        "\n@After",
        "\n}\n",
        "\n\n",
        "\n",
    ]

    TS_SEPARATORS = [
        "\ndescribe(",
        "\nit(",
        "\ntest(",
        "\nfunction ",
        "\nconst ",
        "\nlet ",
        "\nexport ",
        "\n}\n",
        "\n\n",
        "\n",
    ]

    @classmethod
    def chunk_java(cls, text, source_file=""):
        splitter = RecursiveCharacterTextSplitter(
            separators=cls.JAVA_SEPARATORS,
            chunk_size=CODE_CHUNK_SIZE,
            chunk_overlap=CODE_CHUNK_OVERLAP,
            length_function=len,
        )
        chunks = splitter.split_text(text)
        return [
            {"content": c, "source": source_file, "language": "java"}
            for c in chunks
        ]

    @classmethod
    def chunk_typescript(cls, text, source_file=""):
        splitter = RecursiveCharacterTextSplitter(
            separators=cls.TS_SEPARATORS,
            chunk_size=CODE_CHUNK_SIZE,
            chunk_overlap=CODE_CHUNK_OVERLAP,
            length_function=len,
        )
        chunks = splitter.split_text(text)
        return [
            {"content": c, "source": source_file, "language": "typescript"}
            for c in chunks
        ]


class TextChunker:
    @classmethod
    def chunk_text(cls, text, source_file="", chunk_type="general"):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )
        chunks = splitter.split_text(text)
        return [
            {"content": c, "source": source_file, "type": chunk_type}
            for c in chunks
        ]


def chunk_source_code(file_path, content):
    ext = file_path.lower()
    if ext.endswith(".java"):
        return CodeChunker.chunk_java(content, source_file=file_path)
    elif ext.endswith((".ts", ".tsx", ".js")):
        return CodeChunker.chunk_typescript(content, source_file=file_path)
    return TextChunker.chunk_text(content, source_file=file_path, chunk_type="code")


def chunk_pdf_text(file_path, content):
    return TextChunker.chunk_text(content, source_file=file_path, chunk_type="documentation")


def chunk_test_case(file_path, content):
    return TextChunker.chunk_text(content, source_file=file_path, chunk_type="test_case")
