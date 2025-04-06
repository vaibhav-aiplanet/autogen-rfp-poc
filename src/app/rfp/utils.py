from enum import Enum


class Topics(Enum):

    UPLOAD = "upload"

    START = "start"

    PARSE = "parse"
    PARSED = "parsed"
    EXTRACT = "extract"
    EXTRACTED = "extracted"
    GENERATE = "generate"
    GENERATED = "generated"

    SAVE = "save_rfp"


class Agents(Enum):
    MANAGER = "manager"
    PARSER = "parser"
    EXTRACTOR = "extractor"
    SECTION_GENERATOR = "section_generator"
