import json
import re

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.message import Message

class ValidateIntentComponent(Component):
    display_name = "Validar intent"
    description = "Valida se o plano de consulta possui o campo intent igual a 'unknown'"
    icon = "square-terminal"

    inputs = [
        MessageTextInput(
            name="query_plan",
            display_name="Query Plan",
            info="Plano de consulta gerado pela LLM no formato json.",
            tool_mode=False,
            required=True
        )
    ]

    outputs = [
        Output(display_name="True", name="true_result", method="true_response", group_outputs=True),
        Output(display_name="False", name="false_result", method="false_response", group_outputs=True),
    ]

    def _clean_llm_json(self, text):
        text = re.sub(r"```json", "", text)
        text = re.sub(r"```", "", text)
        return text.strip()

    def evaluate_condition(self) -> bool:
        plan_object = json.loads(self._clean_llm_json(self.query_plan))
        return plan_object['intent'] == "unknown"

    def true_response(self) -> Message:
        result = self.evaluate_condition()
        if result:
            return self.query_plan
        else:
            return self.stop(output_name="true_result")
    
    def false_response(self) -> Message:
        result = self.evaluate_condition()
        if not result:
            return self.query_plan
        else:
            return self.stop(output_name="false_result")
