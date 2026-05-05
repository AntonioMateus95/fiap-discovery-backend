import yaml

from lfx.custom.custom_component.component import Component
from lfx.io import MultilineInput, Output
from lfx.schema.data import Data


class SemanticCatalogBuilderComponent(Component):
    display_name = "Montagem do catálogo semântico final"
    description = "Inclui o conjunto de datasets como um atributo do catálogo semântico"
    icon = "square-terminal"

    inputs = [
        MultilineInput(
            name="semantic_catalog",
            display_name="Catálogo semântico genérico",
            info="",
            value="",
            input_types=["Message"],
            tool_mode=False,
            required=True,
        ),
        MultilineInput(
            name="dataset",
            display_name="Conteúdo do dataset suportado pelo modelo",
            info="",
            value="",
            input_types=["Message"],
            tool_mode=False,
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Resultado",
            name="result",
            type_=Data,
            method="execute",
        ),
    ]

    def execute(self) -> Data:
        try:
            _semantic_catalog = yaml.safe_load(self.semantic_catalog)
            _dataset = yaml.safe_load(self.dataset)
            _semantic_catalog['datasets'] = _dataset
            result = yaml.safe_dump(_semantic_catalog, sort_keys=False, allow_unicode=True)

            self.log("Code execution completed successfully")
            return Data(data={"result": result})

        except ImportError as e:
            error_message = f"Import Error: {e!s}"
            self.log(error_message)
            return Data(data={"error": error_message})

        except SyntaxError as e:
            error_message = f"Syntax Error: {e!s}"
            self.log(error_message)
            return Data(data={"error": error_message})

        except (NameError, TypeError, ValueError) as e:
            error_message = f"Error during execution: {e!s}"
            self.log(error_message)
            return Data(data={"error": error_message})

    def build(self):
        return self.execute
