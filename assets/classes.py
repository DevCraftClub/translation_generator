import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional


# Класс, описывающий отдельный переводимый блок (trans-unit)
@dataclass
class TransUnit:
	id: str
	source: str
	target: str
	target_state: Optional[str] = None
	target_state_qualifier: Optional[str] = None
	approved: bool = False


# Класс, описывающий тело файла, содержащее список переводов
@dataclass
class Body:
	trans_units: List[TransUnit] = field(default_factory=list)


# Класс, описывающий элемент <file> с атрибутами и телом
@dataclass
class File:
	original: str
	datatype: str
	source_language: str
	target_language: str
	body: Body


# Основной класс, описывающий документ XLIFF
@dataclass
class Xliff:
	version: str
	file: File

	@classmethod
	def from_xml(cls, xml_content: str) -> 'Xliff':
		# Разбираем XML-строку
		root = ET.fromstring(xml_content)
		version = root.attrib.get("version", "1.2")
		# Определяем пространство имён
		ns = {"xliff": "urn:oasis:names:tc:xliff:document:1.2"}
		file_elem = root.find("xliff:file", ns)
		if file_elem is None:
			raise ValueError("Не найден элемент <file> в XML.")

		original = file_elem.attrib.get("original", "")
		datatype = file_elem.attrib.get("datatype", "")
		source_language = file_elem.attrib.get("source-language", "")
		target_language = file_elem.attrib.get("target-language", "")

		body_elem = file_elem.find("xliff:body", ns)
		if body_elem is None:
			raise ValueError("Не найден элемент <body> в XML.")

		trans_units = []
		for tu in body_elem.findall("xliff:trans-unit", ns):
			tu_id = tu.attrib.get("id", "")
			# Получаем текст из элементов <source> и <target>
			source_elem = tu.find("xliff:source", ns)
			source_text = source_elem.text if source_elem is not None else ""
			target_elem = tu.find("xliff:target", ns)
			target_text = target_elem.text if target_elem is not None else ""
			target_state = target_elem.attrib.get("state") if target_elem is not None else None
			target_state_qualifier = target_elem.attrib.get("state-qualifier") if target_elem is not None else None
			# Если атрибут approved установлен в "yes", то помечаем перевод как одобренный
			approved = True if tu.attrib.get("approved") == "yes" else False

			trans_unit = TransUnit(
					id=tu_id,
					source=source_text,
					target=target_text,
					target_state=target_state,
					target_state_qualifier=target_state_qualifier,
					approved=approved
			)
			trans_units.append(trans_unit)

		body = Body(trans_units=trans_units)
		file_obj = File(
				original=original,
				datatype=datatype,
				source_language=source_language,
				target_language=target_language,
				body=body
		)
		return cls(version=version, file=file_obj)

	def save_to_file(self, file_path: str) -> None:
		"""
		Сохраняет текущий объект Xliff в указанный XML-файл.
		"""
		ns = "urn:oasis:names:tc:xliff:document:1.2"
		# Создаем корневой элемент
		root = ET.Element("xliff", version=self.version, xmlns=ns)
		file_attrib = {
				"original"       : self.file.original,
				"datatype"       : self.file.datatype,
				"source-language": self.file.source_language,
				"target-language": self.file.target_language
		}
		file_elem = ET.SubElement(root, "file", file_attrib)
		body_elem = ET.SubElement(file_elem, "body")

		for tu in self.file.body.trans_units:
			trans_unit_attrib = {"id": tu.id}
			if tu.approved:
				trans_unit_attrib["approved"] = "yes"
			trans_unit_elem = ET.SubElement(body_elem, "trans-unit", trans_unit_attrib)

			source_elem = ET.SubElement(trans_unit_elem, "source")
			source_elem.text = tu.source

			target_attrib = {}
			if tu.target_state:
				target_attrib["state"] = tu.target_state
			if tu.target_state_qualifier:
				target_attrib["state-qualifier"] = tu.target_state_qualifier
			target_elem = ET.SubElement(trans_unit_elem, "target", target_attrib)
			target_elem.text = tu.target

		tree = ET.ElementTree(root)
		tree.write(file_path, encoding="utf-8", xml_declaration=True)
