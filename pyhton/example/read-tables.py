source = "C:\\Users\\thale\\Desktop\\bhas\\1 Askeladd_17.5x26x36in BB HO DWD_BHA Tally_R01.pdf"  # document per local path or URL

import datetime
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from io import BytesIO

start = datetime.datetime.now()

pipeline_options = PdfPipelineOptions(do_table_structure=True)
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE  # use more accurate TableFormer model

doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

bytes_io:BytesIO = None
with open(source, "rb") as buf:
    bytes_io = BytesIO(buf.read())
source = DocumentStream(name="my_doc.pdf", stream=bytes_io)
converter = DocumentConverter()
result = converter.convert(source)
print(result)

end_time = datetime.datetime.now()
print("Time taken: ", (end_time - start).total_seconds(), " seconds")
