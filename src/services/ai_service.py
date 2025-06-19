from typing import List, Dict
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import openai, json, os, asyncio, textwrap

MAX_TOKENS_PER_CHUNK = 3000

class AIService:
    def __init__(self):
        self.logs_dir = Path("ai_logs")
        self.corrections_file = Path("ai_corrections.jsonl")
        self.docs_version = "2.0"
        self.model = "deepseek-chat"
        os.makedirs(self.logs_dir, exist_ok=True)
        load_dotenv()
        
    def split_code_by_tokens(self, content: str, max_tokens: int = MAX_TOKENS_PER_CHUNK) -> List[str]:
        lines = content.splitlines()
        chunks = []
        current_chunk = []
        current_length = 0

        for line in lines:
            line_len = len(line.split())
            if current_length + line_len > max_tokens:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_length = line_len
            else:
                current_chunk.append(line)
                current_length += line_len

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def build_prompt(
        self,
        file_name: str,
        file_path: str,
        content: str,
        dependencies: List[str],
    ) -> str:
        """Строит промт для генерации документации с учетом старой версии (если есть)"""
        
        prompt = f"""
            Ты — технический писатель и аналитик. Ниже представлен код проекта.

            Вот код проекта:
            {content}
            
            Тебе требуется сгенерировать подробный и понятную, исчерпывающую профессиональную документацию для кода. 
            В документации (документация должна составляться сверху вниз в соотвествие с кодом) должно содержаться следующее,
            1. Название класса и его описание
            2. Методы и функции которые содержит класс
            3. Описание каждой функции, для какой цели она используется (как ты думаешь)
            4. Должно быть для каждой функции входные параметры
            5. Также должно быть, что может вывести функция
            
            Прошу именно с такой структурой которой я тебе описал, разработать документацию в соответствии ВСЕГО КОДА КОТОРЫЙ БУДЕТ НИЖЕ
            
            **Стиль написания**:
                - Используй профессиональный, но понятный язык
                - Для каждого метода укажи его сложность (O-нотация)
                - Технические термины выделяй `backticks`
                - Код оформляй в блоки ``` с указанием языка
                - Списки и подсписки для пошаговых объяснений
                - Важные предупреждения выделяй **Внимание:** или ⚠️
                - Возможные проблемы при настройке выделяй **Осторожно* или ❗️
                - Не должно быть лишней информации (пример: Вот профессиональная документация для предоставленного кода:, Эта документация:, Path 1) ИХ НЕ ДОЛЖНО БЫТЬ
                - Добавляй документацию к библиотекам которые есть проекте в конец сообщения (если есть alembic ты приклепляешь документацию к alembic, только не забудь про язые програмирования чтоыб правильно указать)
                - Вся документация должна быть на русском. При создание документации НЕ НАДО ОБОРАЧИВАТЬ ее в ```markdown ```
                - в начале документации должно добавляться кликабельное содержание для передвижения по документации
                
            Вот тебе название файла: {file_name}
            Зависимости внутри файла: {', '.join(dependencies)}
            И последнее его место нахождение в проекте: {file_path}
        """

        return "\n".join(prompt)
    
    def generate_documentation_sync(self, content: str, file_path: str, dependencies: List[str]) -> str:
        """Синхронная обертка для вызова async generate_documentation (для использования в ProcessPoolExecutor)"""
        return asyncio.run(self.generate_documentation(content, file_path, dependencies))

    async def generate_documentation(
        self,
        content: str,
        file_path: str,
        dependencies: List[str],
    ) -> str:
        """Генерирует документацию с возможностью обновления существующей"""
        self._log_processing_start(file_path)
        
        chunks = self.split_code_by_tokens(content)
        client = openai.OpenAI(
            api_key=os.getenv("TOKEN_OPENAI_API"),
            base_url="https://api.proxyapi.ru/deepseek"
        )

        full_result = ""
        for i, chunk in enumerate(chunks):
            prompt = self.build_prompt(
                os.path.basename(file_path),
                file_path,
                chunk,
                dependencies
            )

            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'Ты являешься специалистом, который разрабатывает документацию к коду. Ты структурируешь и пишешь четкую документацию с использованием Markdown и Readme.md.'},
                    {'role': 'user', 'content': prompt}
                ]
            )
            full_result += f"\n\n## Part {i + 1}\n" + completion.choices[0].message.content.strip()

        self._log_processing_end(file_path, full_result)
        return full_result

    def _log_processing_start(self, file_path: str):
        self._write_log({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "start_processing",
            "file": file_path
        })

    def _log_processing_end(self, file_path: str, result: str):
        self._write_log({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "end_processing",
            "file": file_path,
            "result_length": len(result)
        })

    def _write_log(self, entry: Dict):
        log_file = self.logs_dir / f"docs_gen_{datetime.utcnow().date()}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def save_correction(self, file_path: str, original_docs: str, corrected_docs: str, rating: int = 5):
        with open(self.corrections_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "file": file_path,
                "original": original_docs,
                "corrected": corrected_docs,
                "rating": rating,
                "version": self.docs_version
            }, ensure_ascii=False) + "\n")