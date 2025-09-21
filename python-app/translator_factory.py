import logging
from translator_gemini import TranslatorGemini


class TranslatorFactory:
    @staticmethod
    def create_translator(settings):
        """สร้าง translator ตามประเภทของ model ที่กำหนดใน settings"""
        try:
            api_params = settings.get_api_parameters()
            if not api_params:
                logging.error("No API parameters found in settings")
                raise ValueError("No API parameters found in settings")

            model = api_params.get("model")
            logging.info(f"Creating translator for model: {model}")

            if not model:
                logging.error("No model specified in API parameters")
                raise ValueError("No model specified in API parameters")

            # ตรวจสอบประเภทของ model
            model_type = TranslatorFactory.validate_model_type(model)
            if not model_type:
                logging.error(f"Unknown model type for: {model}")
                raise ValueError(f"Unknown model type for: {model}")

            logging.info(f"Validated model type: {model_type} for model: {model}")

            # สร้าง Gemini translator เท่านั้น
            logging.info(f"Creating Gemini Translator with model: {model}")
            translator = TranslatorGemini(settings)
            logging.info(
                f"Successfully created TranslatorGemini instance: {type(translator).__name__}"
            )
            return translator

        except Exception as e:
            logging.error(f"Error creating translator: {str(e)}")
            # ถ้าเกิดข้อผิดพลาด ให้ให้รู้ว่าเกิดปัญหา
            raise ValueError(f"Failed to create translator: {str(e)}")

    @staticmethod
    def validate_model_type(model):
        """ตรวจสอบประเภทของ model - รองรับเฉพาะ Gemini เท่านั้น"""
        logging.info(f"Model '{model}' identified as Gemini type")
        return "gemini"
