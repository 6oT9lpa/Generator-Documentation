import os
import re
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, Set, List, Tuple, Optional


class DependencyAnalyzer:
    SUPPORTED_EXTENSIONS = {
        # Основные языки
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React JSX',
        '.tsx': 'React TSX',
        '.mjs': 'JavaScript Module',
        '.cjs': 'CommonJS',
        
        # Веб и разметка
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'Sass',
        '.less': 'Less',
        '.sass': 'Sass',
        '.vue': 'Vue.js',
        '.svelte': 'Svelte',
        
        # Мобильная разработка
        '.kt': 'Kotlin',
        '.swift': 'Swift',
        '.dart': 'Dart',
        
        # Си-подобные языки
        '.c': 'C',
        '.cpp': 'C++',
        '.h': 'C Header',
        '.hpp': 'C++ Header',
        '.cs': 'C#',
        '.java': 'Java',
        '.go': 'Go',
        '.rs': 'Rust',
        
        # Функциональные языки
        '.hs': 'Haskell',
        '.elm': 'Elm',
        '.clj': 'Clojure',
        '.scala': 'Scala',
        '.erl': 'Erlang',
        
        # Скриптовые языки
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.pl': 'Perl',
        '.lua': 'Lua',
        '.sh': 'Bash Script',
        
        # Другие
        '.groovy': 'Groovy',
        '.r': 'R',
        '.jl': 'Julia',
        '.d': 'D',
        '.zig': 'Zig',
        '.nim': 'Nim',
        '.v': 'V',
        
        # Конфигурационные файлы
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.toml': 'TOML',
        '.xml': 'XML',
        
        # WebAssembly
        '.wat': 'WebAssembly Text',
        '.wasm': 'WebAssembly Binary',
        
        # SQL
        '.sql': 'SQL',
        
        # Протофайлы
        '.proto': 'Protocol Buffers'
    }

    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        if not os.path.isdir(self.repo_path):
            raise ValueError(f"Invalid repository path: {self.repo_path}")
        self.files_by_extension = defaultdict(list)
        self._collect_files()

    def _collect_files(self):
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    abs_path = os.path.join(root, file)
                    self.files_by_extension[ext].append(abs_path)

    def group_files_by_dependencies(self) -> Tuple[List[Set[str]], Dict[str, Dict]]:
        graph = self._build_dependency_graph()
        visited = set()
        groups = []
        file_details = {}
        
        for file_path in graph:
            file_details[file_path] = self._analyze_file_contents(file_path)
        
        for node in graph:
            if node not in visited:
                group = set()
                queue = deque([node])
                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue
                    visited.add(current)
                    group.add(current)
                    queue.extend(graph[current] - visited)
                groups.append(group)
        
        self._generate_group_reports(groups, file_details, graph)
        
        return groups, file_details
    
    def _generate_group_reports(self, groups: List[Set[str]], file_details: Dict, graph: Dict):
        """Генерирует отчеты для каждой группы файлов"""
        report_dir = os.path.join(self.repo_path, "_dependency_reports")
        os.makedirs(report_dir, exist_ok=True)
        
        for i, group in enumerate(groups, 1):
            group_name = f"group_{i}"
            report_path = os.path.join(report_dir, f"{group_name}_report.txt")
            
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"=== Dependency Report for {group_name} ===\n")
                f.write(f"Files in group: {len(group)}\n\n")
                
                for file_path in group:
                    details = file_details.get(file_path, {})
                    dependencies = graph.get(file_path, set())
                    
                    f.write(f"\n--- File: {file_path} ---\n")
                    f.write(f"Language: {details.get('language', 'Unknown')}\n")
                    f.write(f"Size: {details.get('size', 0)} bytes\n")
                    
                    f.write("\nDependencies:\n")
                    for dep in dependencies:
                        f.write(f"- {dep}\n")
                    
                    if details.get('functions'):
                        f.write("\nFunctions:\n")
                        for func in details['functions']:
                            f.write(f"- {func['name']}({', '.join(func['params'])})\n")
                    
                    if details.get('classes'):
                        f.write("\nClasses:\n")
                        for cls in details['classes']:
                            f.write(f"- {cls['name']}\n")
                    
                    f.write("\n" + "="*50 + "\n")

    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        graph: Dict[str, Set[str]] = defaultdict(set)
        file_map = self._build_relative_path_map()

        for ext, files in self.files_by_extension.items():
            for file_path in files:
                rel_file = os.path.relpath(file_path, self.repo_path)
                graph[rel_file]

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue

                dependencies = self._extract_dependencies(content, ext)
                for dep in dependencies:
                    dep_path = self._resolve_dependency(file_path, dep)
                    if not dep_path:
                        continue
                    rel_dep = os.path.relpath(dep_path, self.repo_path)
                    if rel_dep in file_map:
                        graph[rel_file].add(rel_dep)
                        graph[rel_dep].add(rel_file)

        return graph

    def _build_relative_path_map(self) -> Dict[str, str]:
        file_map = {}
        for ext, files in self.files_by_extension.items():
            for abs_path in files:
                rel_path = os.path.relpath(abs_path, self.repo_path)
                file_map[rel_path] = abs_path
        return file_map

    def _resolve_dependency(self, current_file: str, dep: str) -> Optional[str]:
        base_dir = os.path.dirname(current_file)
        
        # Попробуем разрешить как относительный путь
        possible_paths = [
            os.path.normpath(os.path.join(base_dir, dep)),
            os.path.normpath(os.path.join(base_dir, dep + '.js')),
            os.path.normpath(os.path.join(base_dir, dep, 'index.js')),
            os.path.normpath(os.path.join(base_dir, dep + '.ts')),
            os.path.normpath(os.path.join(base_dir, dep, 'index.ts')),
            os.path.normpath(os.path.join(base_dir, dep + '.mjs')),
            os.path.normpath(os.path.join(base_dir, dep + '.cjs')),
        ]
        
        # Добавим пути для других языков
        for ext in self.SUPPORTED_EXTENSIONS:
            possible_paths.append(os.path.normpath(os.path.join(base_dir, dep + ext)))
            possible_paths.append(os.path.normpath(os.path.join(base_dir, dep, 'index' + ext)))
        
        # Проверим все возможные пути
        for path in possible_paths:
            if os.path.isfile(path):
                return path
        
        # Попробуем найти в node_modules
        if '/' not in dep and '\\' not in dep:
            node_modules_path = os.path.join(base_dir, 'node_modules', dep)
            package_json_path = os.path.join(node_modules_path, 'package.json')
            if os.path.exists(package_json_path):
                try:
                    import json
                    with open(package_json_path, 'r', encoding='utf-8') as f:
                        package_data = json.load(f)
                    main_file = package_data.get('main', 'index.js')
                    return os.path.join(node_modules_path, main_file)
                except:
                    pass
        
        return None
    
    def _extract_dependencies(self, content: str, ext: str) -> Set[str]:
        if ext == ".py":
            return self._parse_python(content)
        elif ext in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
            return self._parse_javascript(content)
        elif ext == ".html":
            return self._parse_html(content)
        elif ext in {".scss", ".sass", ".less"}:
            return self._parse_css(content)
        elif ext == ".vue":
            return self._parse_vue(content)
        elif ext == ".svelte":
            return self._parse_svelte(content)
        elif ext in {".c", ".cpp", ".h", ".hpp"}:
            return self._parse_cpp(content)
        elif ext == ".cs":
            return self._parse_csharp(content)
        elif ext == ".java":
            return self._parse_java(content)
        elif ext == ".go":
            return self._parse_go(content)
        elif ext == ".rs":
            return self._parse_rust(content)
        elif ext == ".kt":
            return self._parse_kotlin(content)
        elif ext == ".swift":
            return self._parse_swift(content)
        elif ext == ".dart":
            return self._parse_dart(content)
        elif ext == ".rb":
            return self._parse_ruby(content)
        elif ext == ".php":
            return self._parse_php(content)
        elif ext == ".hs":
            return self._parse_haskell(content)
        elif ext == ".lua":
            return self._parse_lua(content)
        elif ext == ".sh":
            return self._parse_shell(content)
        elif ext == ".r":
            return self._parse_r(content)
        elif ext == ".jl":
            return self._parse_julia(content)
        elif ext == ".zig":
            return self._parse_zig(content)
        elif ext == ".nim":
            return self._parse_nim(content)
        elif ext == ".v":
            return self._parse_v(content)
        elif ext == ".proto":
            return self._parse_proto(content)
        else:
            return set()
    
    def _analyze_file_contents(self, file_path: str) -> Dict:
        """Анализирует содержимое файла и возвращает структурированную информацию"""
        abs_path = os.path.join(self.repo_path, file_path)
        if not os.path.exists(abs_path):
            return {}
        
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return {}
        
        ext = os.path.splitext(file_path)[1].lower()
        language = self.SUPPORTED_EXTENSIONS.get(ext, "Unknown")
        
        analysis = {
            "path": file_path,
            "language": language,
            "size": os.path.getsize(abs_path),
            "functions": [],
            "classes": [],
            "imports": list(self._extract_dependencies(content, ext)),
            "analysis": self._analyze_code_structure(content, ext)
        }
        
        return analysis
    
    def _analyze_code_structure(self, content: str, ext: str) -> Dict:
        """Анализирует структуру кода в файле"""
        if ext == ".py":
            return self._analyze_python_structure(content)
        elif ext in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
            return self._analyze_javascript_structure(content)
        elif ext in {".c", ".cpp", ".h", ".hpp"}:
            return self._analyze_cpp_structure(content)
        elif ext == ".cs":
            return self._analyze_csharp_structure(content)
        elif ext == ".java":
            return self._analyze_java_structure(content)
        elif ext == ".go":
            return self._analyze_go_structure(content)
        elif ext == ".rs":
            return self._analyze_rust_structure(content)
        elif ext == ".kt":
            return self._analyze_kotlin_structure(content)
        elif ext == ".swift":
            return self._analyze_swift_structure(content)
        elif ext == ".dart":
            return self._analyze_dart_structure(content)
        elif ext == ".rb":
            return self._analyze_ruby_structure(content)
        elif ext == ".php":
            return self._analyze_php_structure(content)
        elif ext == ".hs":
            return self._analyze_haskell_structure(content)
        elif ext == ".lua":
            return self._analyze_lua_structure(content)
        elif ext == ".vue":
            return self._analyze_vue_structure(content)
        elif ext == ".svelte":
            return self._analyze_svelte_structure(content)
        else:
            return {}

    # -------- Анализаторы функций ---------
    
    def _analyze_python_structure(self, content: str) -> Dict:
        """Анализирует структуру Python файла"""
        analysis = {
            "functions": [],
            "classes": [],
            "global_vars": []
        }
        
        # Поиск функций
        func_matches = re.finditer(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(1),
                "params": [p.strip() for p in match.group(2).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })
        
        # Поиск классов
        class_matches = re.finditer(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })
        
        return analysis
    
    def _analyze_javascript_structure(self, content: str) -> Dict:
        """Анализирует структуру JavaScript/TypeScript файла"""
        analysis = {
            "functions": [],
            "classes": [],
            "global_vars": []
        }

        # Функции: function имя(...) или const имя = (...) => { ... }
        func_matches = re.finditer(
            r'(?:function\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\))|(?:const\s+([a-zA-Z0-9_]+)\s*=\s*\(([^)]*)\)\s*=>)',
            content)
        for match in func_matches:
            name = match.group(1) or match.group(3)
            params = match.group(2) or match.group(4) or ''
            analysis["functions"].append({
                "name": name,
                "params": [p.strip() for p in params.split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Классы
        class_matches = re.finditer(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_cpp_structure(self, content: str) -> Dict:
        """Анализирует структуру C++ файла"""
        analysis = {
            "functions": [],
            "classes": [],
            "global_vars": []
        }

        # Функции: возвращаемый_тип имя(параметры) { ... }
        func_matches = re.finditer(r'([a-zA-Z_][a-zA-Z0-9_:<>]*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*\{',
                                content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(2),
                "params": [p.strip() for p in match.group(3).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Классы
        class_matches = re.finditer(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_csharp_structure(self, content: str) -> Dict:
        """Анализирует структуру C# файла"""
        analysis = {
            "functions": [],
            "classes": [],
            "global_vars": []
        }

        # Методы: тип имя(параметры)
        func_matches = re.finditer(r'\b(?:public|private|protected|internal|static|\s)*\s*([a-zA-Z0-9_<>,\[\]]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)',
                                content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(2),
                "params": [p.strip() for p in match.group(3).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Классы
        class_matches = re.finditer(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis
    
    def _analyze_java_structure(self, content: str) -> Dict:
        """Анализирует структуру Java файла"""
        analysis = {
            "functions": [],
            "classes": [],
            "global_vars": []
        }

        # Методы
        func_matches = re.finditer(r'\b(?:public|private|protected|static|\s)*\s*([a-zA-Z0-9_<>,\[\]]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)',
                                content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(2),
                "params": [p.strip() for p in match.group(3).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Классы
        class_matches = re.finditer(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_go_structure(self, content: str) -> Dict:
        """Анализирует структуру Go файла"""
        analysis = {
            "functions": [],
            "structs": [],
            "interfaces": []
        }

        # Функции
        func_matches = re.finditer(r'func\s+(?:\([^)]*\)\s*)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(1),
                "params": [p.strip() for p in match.group(2).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Структуры
        struct_matches = re.finditer(r'type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+struct', content)
        for match in struct_matches:
            analysis["structs"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        # Интерфейсы
        interface_matches = re.finditer(r'type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+interface', content)
        for match in interface_matches:
            analysis["interfaces"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_rust_structure(self, content: str) -> Dict:
        """Анализирует структуру Rust файла"""
        analysis = {
            "functions": [],
            "classes": [],
            "global_vars": []
        }

        # Функции
        func_matches = re.finditer(r'\bfn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(1),
                "params": [p.strip() for p in match.group(2).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Структуры
        struct_matches = re.finditer(r'\bstruct\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in struct_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        # Энумы
        enum_matches = re.finditer(r'\benum\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in enum_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis
    
    def _analyze_svelte_structure(self, content: str) -> Dict:
        """Анализирует структуру Svelte компонента"""
        analysis = {
            "script": {
                "variables": [],
                "functions": [],
                "imports": []
            },
            "markup": {
                "components": [],
                "elements": []
            },
            "style": {
                "rules": []
            }
        }

        # Анализ script секции
        script_match = re.search(r'<script[^>]*>([\s\S]*?)<\/script>', content)
        if script_match:
            script_content = script_match.group(1)
            # Импорты
            analysis["script"]["imports"] = list(self._parse_javascript(script_content))
            # Переменные
            analysis["script"]["variables"] = [
                {"name": m.group(1), "line": script_content[:m.start()].count('\n') + 1}
                for m in re.finditer(r'let\s+([a-zA-Z_][a-zA-Z0-9_]*)', script_content)
            ]
            # Функции
            analysis["script"]["functions"] = [
                {
                    "name": m.group(1),
                    "params": [p.strip() for p in m.group(2).split(',') if p.strip()],
                    "line": script_content[:m.start()].count('\n') + 1
                }
                for m in re.finditer(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', script_content)
            ]

        # Анализ markup секции
        markup_match = re.search(r'<[^>]+>', content)
        if markup_match:
            # Компоненты (теги с заглавной буквы)
            analysis["markup"]["components"] = [
                {"name": m.group(1), "line": content[:m.start()].count('\n') + 1}
                for m in re.finditer(r'<([A-Z][a-zA-Z0-9]*)', content)
            ]
            # HTML элементы
            analysis["markup"]["elements"] = [
                {"name": m.group(1), "line": content[:m.start()].count('\n') + 1}
                for m in re.finditer(r'<([a-z][a-zA-Z0-9-]*)', content)
            ]

        # Анализ style секции
        style_match = re.search(r'<style[^>]*>([\s\S]*?)<\/style>', content)
        if style_match:
            style_content = style_match.group(1)
            # CSS правила
            analysis["style"]["rules"] = [
                {"selector": m.group(1).strip(), "line": style_content[:m.start()].count('\n') + 1}
                for m in re.finditer(r'([^{]+)\s*\{', style_content)
            ]

        return analysis
    
    def _analyze_kotlin_structure(self, content: str) -> Dict:
        """Анализирует структуру Kotlin файла"""
        analysis = {
            "functions": [],
            "classes": []
        }

        # Функции
        func_matches = re.finditer(r'\bfun\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(1),
                "params": [p.strip() for p in match.group(2).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Классы
        class_matches = re.finditer(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_swift_structure(self, content: str) -> Dict:
        """Анализирует структуру Swift файла"""
        analysis = {
            "functions": [],
            "classes": [],
            "structs": [],
            "enums": [],
            "protocols": []
        }

        # Функции
        func_matches = re.finditer(r'\bfunc\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(1),
                "params": [p.strip() for p in match.group(2).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Классы
        class_matches = re.finditer(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        # Структуры
        struct_matches = re.finditer(r'\bstruct\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in struct_matches:
            analysis["structs"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        # Энумы
        enum_matches = re.finditer(r'\benum\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in enum_matches:
            analysis["enums"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        # Протоколы
        protocol_matches = re.finditer(r'\bprotocol\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in protocol_matches:
            analysis["protocols"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_dart_structure(self, content: str) -> Dict:
        """Анализирует структуру Dart файла"""
        analysis = {
            "functions": [],
            "classes": []
        }

        # Функции
        func_matches = re.finditer(r'\b(?:void|int|double|String|bool|var|dynamic|const|final)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(1),
                "params": [p.strip() for p in match.group(2).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Классы
        class_matches = re.finditer(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_ruby_structure(self, content: str) -> Dict:
        """Анализирует структуру Ruby файла"""
        analysis = {
            "methods": [],
            "classes": [],
            "modules": []
        }

        # Методы
        method_matches = re.finditer(r'\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(?([^)]*)\)?', content)
        for match in method_matches:
            analysis["methods"].append({
                "name": match.group(1),
                "params": [p.strip() for p in match.group(2).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Классы
        class_matches = re.finditer(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        # Модули
        module_matches = re.finditer(r'\bmodule\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in module_matches:
            analysis["modules"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_php_structure(self, content: str) -> Dict:
        """Анализирует структуру PHP файла"""
        analysis = {
            "functions": [],
            "classes": []
        }

        # Функции
        func_matches = re.finditer(r'\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(1),
                "params": [p.strip() for p in match.group(2).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Классы
        class_matches = re.finditer(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_haskell_structure(self, content: str) -> Dict:
        """Анализирует структуру Haskell файла"""
        analysis = {
            "functions": [],
            "data_types": [],
            "type_classes": []
        }

        # Функции
        func_matches = re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*::\s*([^=]+)=', content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(1),
                "type": match.group(2).strip(),
                "line": content[:match.start()].count('\n') + 1
            })

        # Типы данных
        data_matches = re.finditer(r'\bdata\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in data_matches:
            analysis["data_types"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        # Классы типов
        class_matches = re.finditer(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        for match in class_matches:
            analysis["type_classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_lua_structure(self, content: str) -> Dict:
        """Анализирует структуру Lua файла"""
        analysis = {
            "functions": [],
            "tables": []
        }

        # Функции
        func_matches = re.finditer(r'\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', content)
        for match in func_matches:
            analysis["functions"].append({
                "name": match.group(1),
                "params": [p.strip() for p in match.group(2).split(',') if p.strip()],
                "line": content[:match.start()].count('\n') + 1
            })

        # Таблицы
        table_matches = re.finditer(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\{', content)
        for match in table_matches:
            analysis["tables"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })

        return analysis

    def _analyze_vue_structure(self, content: str) -> Dict:
        """Анализирует структуру Vue файла"""
        analysis = {
            "components": [],
            "methods": [],
            "data": [],
            "computed": [],
            "props": []
        }

        # Компоненты
        component_matches = re.finditer(r'components:\s*\{([^}]+)\}', content)
        for match in component_matches:
            component_names = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)', match.group(1))
            for name in component_names:
                analysis["components"].append({
                    "name": name,
                    "line": content[:match.start()].count('\n') + 1
                })

        # Методы
        method_matches = re.finditer(r'methods:\s*\{([^}]+)\}', content)
        for match in method_matches:
            method_defs = re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', match.group(1))
            for m in method_defs:
                analysis["methods"].append({
                    "name": m.group(1),
                    "params": [p.strip() for p in m.group(2).split(',') if p.strip()],
                    "line": content[:match.start()].count('\n') + 1
                })

        return analysis
    
    # -------- Parsers --------

    def _parse_python(self, content: str) -> Set[str]:
        deps = set()
        from_imports = re.findall(r'from\s+([a-zA-Z0-9_.]+)\s+import', content)
        direct_imports = re.findall(r'^\s*import\s+([a-zA-Z0-9_.]+)', content, re.MULTILINE)
        all_imports = from_imports + direct_imports

        for imp in all_imports:
            parts = imp.split(".")
            if parts:
                deps.add(os.path.join(*parts) + ".py")

        wildcard_imports = re.findall(r'from\s+([a-zA-Z0-9_.]+)\s+import\s+\*', content)
        for imp in wildcard_imports:
            parts = imp.split(".")
            if parts:
                deps.add(os.path.join(*parts, "__init__.py"))

        return deps

    def _parse_html(self, content: str) -> Set[str]:
        deps = set()
        scripts = re.findall(r'<script.*?src=["\'](.+?)["\']', content)
        links = re.findall(r'<link.*?href=["\'](.+?)["\']', content)
        images = re.findall(r'<img.*?src=["\'](.+?)["\']', content)
        anchors = re.findall(r'<a.*?href=["\'](.+?)["\']', content)
        
        deps.update(scripts)
        deps.update(links)
        deps.update(images)
        deps.update(anchors)
        return deps
    
    def _parse_css(self, content: str) -> Set[str]:
        deps = set()
        imports = re.findall(r'@import\s+(?:url\()?["\'](.+?)["\']\)?', content)
        urls = re.findall(r'url\(["\']?(.+?)["\']?\)', content)
        
        deps.update(imports)
        deps.update(urls)
        return deps
    
    def _parse_vue(self, content: str) -> Set[str]:
        deps = set()
        # Импорты в script секции
        script_matches = re.search(r'<script[^>]*>([\s\S]*?)<\/script>', content)
        if script_matches:
            script_content = script_matches.group(1)
            deps.update(self._parse_javascript(script_content))
        
        # Импорты в template секции
        template_matches = re.search(r'<template[^>]*>([\s\S]*?)<\/template>', content)
        if template_matches:
            template_content = template_matches.group(1)
            deps.update(self._parse_html(template_content))
        
        # Импорты в style секции
        style_matches = re.findall(r'<style[^>]*>([\s\S]*?)<\/style>', content)
        for style_content in style_matches:
            deps.update(self._parse_css(style_content))
        
        return deps

    def _parse_svelte(self, content: str) -> Set[str]:
        deps = set()
        # Импорты в script секции
        script_matches = re.search(r'<script[^>]*>([\s\S]*?)<\/script>', content)
        if script_matches:
            script_content = script_matches.group(1)
            deps.update(self._parse_javascript(script_content))
        
        # HTML-подобные зависимости
        html_matches = re.search(r'<[^>]+>', content)
        if html_matches:
            deps.update(self._parse_html(html_matches.group(0)))
        
        return deps

    def _parse_cpp(self, content: str) -> Set[str]:
        return set(re.findall(r'#include\s+[<"](.+?)[>"]', content))

    def _parse_csharp(self, content: str) -> Set[str]:
        deps = set()
        
        usings = re.findall(r'using\s+([a-zA-Z0-9_.]+);', content)
        deps.update(usings)
        
        assemblies = re.findall(r'\[assembly:\s*[^\]]+\s*\(\s*@"([^"]+)"\s*\)\s*\]', content)
        deps.update(assemblies)
        
        return deps

    def _parse_java(self, content: str) -> Set[str]:
        deps = set()

        imports = re.findall(r'import\s+(?:static\s+)?([a-zA-Z0-9_.]+)\s*;', content)
        deps.update(imports)
        
        packages = re.findall(r'package\s+([a-zA-Z0-9_.]+)\s*;', content)
        deps.update(packages)
        
        return deps

    def _parse_go(self, content: str) -> Set[str]:
        deps = set()

        imports = re.findall(r'import\s+(?:(?:\w+\s+)?"([^"]+)"', content)
        deps.update(imports)
        

        multiline_imports = re.findall(r'import\s*\(\s*([^)]+)\s*\)', content)
        for imp_group in multiline_imports:
            lines = [line.strip().strip('"') for line in imp_group.split('\n') if line.strip()]
            deps.update(lines)
        
        return deps

    def _parse_rust(self, content: str) -> Set[str]:
        deps = set()

        mod_matches = re.findall(r'\b(?:pub\s+)?mod\s+([a-zA-Z0-9_]+)\s*;', content)
        for mod_name in mod_matches:
            deps.add(f"{mod_name}.rs")
            deps.add(os.path.join(mod_name, "mod.rs"))

        use_matches = re.findall(r'\buse\s+([a-zA-Z0-9_:]+)', content)
        for use_path in use_matches:
            segments = use_path.split("::")

            candidate_path = os.path.join(*segments) + ".rs"
            deps.add(candidate_path)
            deps.add(os.path.join(*segments, "mod.rs"))

        return deps

    def _parse_kotlin(self, content: str) -> Set[str]:
        deps = set()
        imports = re.findall(r'import\s+([a-zA-Z0-9_.]+)', content)
        deps.update(imports)
        
        packages = re.findall(r'package\s+([a-zA-Z0-9_.]+)', content)
        deps.update(packages)
        
        return deps

    def _parse_swift(self, content: str) -> Set[str]:
        deps = set()
        imports = re.findall(r'import\s+([a-zA-Z0-9_]+)', content)
        deps.update(imports)
        
        return deps

    def _parse_dart(self, content: str) -> Set[str]:
        deps = set()
        imports = re.findall(r'import\s+[\'\"]([^\'\"]+)[\'\"]', content)
        deps.update(imports)
        
        package_imports = re.findall(r'package:([^\'\"\s]+)', content)
        deps.update(package_imports)
        
        return deps

    def _parse_ruby(self, content: str) -> Set[str]:
        deps = set()
        requires = re.findall(r'require\s+[\'"]([^\'"]+)[\'"]', content)
        deps.update(requires)
        
        loads = re.findall(r'load\s+[\'"]([^\'"]+)[\'"]', content)
        deps.update(loads)
        

        autoloads = re.findall(r'autoload\s+:[A-Za-z0-9_]+\s*,\s*[\'"]([^\'"]+)[\'"]', content)
        deps.update(autoloads)
        
        return deps

    def _parse_php(self, content: str) -> Set[str]:
        deps = set()

        requires = re.findall(r'(?:require|include)(?:_once)?\s*[\'"]([^\'"]+)[\'"]', content)
        deps.update(requires)
        
        uses = re.findall(r'use\s+([a-zA-Z0-9_\\]+)', content)
        deps.update(uses)
        
        autoloads = re.findall(r'spl_autoload_register\s*\(.*?["\']([^"\']+)["\']', content)
        deps.update(autoloads)
        
        return deps

    def _parse_haskell(self, content: str) -> Set[str]:
        deps = set()
        imports = re.findall(r'import\s+(?:qualified\s+)?([a-zA-Z0-9.]+)', content)
        deps.update(imports)
        
        return deps

    def _parse_lua(self, content: str) -> Set[str]:
        deps = set()
        requires = re.findall(r'require\s*\(?[\'"]([^\'"]+)[\'"]\)?', content)
        deps.update(requires)
        
        return deps

    def _parse_r(self, content: str) -> Set[str]:
        deps = set()
        imports = re.findall(r'library\s*\(([^)]+)\)', content)
        deps.update(imports)
        
        sources = re.findall(r'source\s*\(["\']([^"\']+)["\']\)', content)
        deps.update(sources)
        
        return deps

    def _parse_julia(self, content: str) -> Set[str]:
        deps = set()
        imports = re.findall(r'(?:using|import)\s+([a-zA-Z0-9.]+)', content)
        deps.update(imports)
        
        includes = re.findall(r'include\s*\(["\']([^"\']+)["\']\)', content)
        deps.update(includes)
        
        return deps

    def _parse_zig(self, content: str) -> Set[str]:
        deps = set()
        imports = re.findall(r'@import\s*\(["\']([^"\']+)["\']\)', content)
        deps.update(imports)
        
        return deps

    def _parse_nim(self, content: str) -> Set[str]:
        deps = set()
        imports = re.findall(r'import\s+([a-zA-Z0-9.]+)', content)
        deps.update(imports)
        
        includes = re.findall(r'include\s+["\']([^"\']+)["\']', content)
        deps.update(includes)
        
        return deps

    def _parse_v(self, content: str) -> Set[str]:
        deps = set()
        
        imports = re.findall(r'import\s+([a-zA-Z0-9.]+)', content)
        deps.update(imports)
        
        return deps

    def _parse_proto(self, content: str) -> Set[str]:
        deps = set()

        imports = re.findall(r'import\s+"([^"]+)"', content)
        deps.update(imports)
        
        return deps
    
    def _parse_shell(self, content: str) -> Set[str]:
        """Парсит зависимости в shell-скриптах"""
        deps = set()
        
        sources = re.findall(r'source\s+["\']?([^"\'\s]+)', content)
        dots = re.findall(r'\.\s+["\']?([^"\'\s]+)', content)
        execs = re.findall(r'(?:sh|bash|\./)\s+([^\s&|;]+)', content)
        
        deps.update(sources)
        deps.update(dots)
        deps.update(execs)
        return deps
    
    def _parse_javascript(self, content: str) -> Set[str]:
        deps = set()

        imports = re.findall(r'import.*?["\'](.+?)["\']', content)
        deps.update(imports)

        requires = re.findall(r'require\(["\'](.+?)["\']\)', content)
        deps.update(requires)

        normalized_deps = set()
        for dep in deps:
            if not any(dep.endswith(ext) for ext in self.SUPPORTED_EXTENSIONS):
                dep += ".js"
            normalized_deps.add(dep)

        return normalized_deps
    
    def generate_visualization(self, groups: List[Set[str]], file_details: Dict[str, Dict]):
        """Генерирует визуализацию зависимостей в формате DOT"""
        dot_dir = os.path.join(self.repo_path, "_dependency_visualization")
        os.makedirs(dot_dir, exist_ok=True)
        
        for i, group in enumerate(groups, 1):
            dot_path = os.path.join(dot_dir, f"group_{i}.dot")
            
            with open(dot_path, "w", encoding="utf-8") as f:
                f.write("digraph dependencies {\n")
                f.write('    node [shape=box, style="rounded,filled", fillcolor="#f0f0f0"];\n')
                f.write('    rankdir="LR";\n\n')
                
                for file_path in group:
                    details = file_details.get(file_path, {})
                    lang = details.get("language", "Unknown")
                    size = details.get("size", 0)
                    func_count = len(details.get("functions", []))
                    class_count = len(details.get("classes", []))
                    
                    label = (
                        f"{file_path}\\n"
                        f"Language: {lang}\\n"
                        f"Size: {size} bytes\\n"
                        f"Functions: {func_count}\\n"
                        f"Classes: {class_count}"
                    )
                    
                    f.write(f'    "{file_path}" [label="{label}"];\n')
                
                for file_path in group:
                    for dep in details.get("imports", []):
                        if dep in group: 
                            f.write(f'    "{file_path}" -> "{dep}";\n')
                
                f.write("}\n")
        
        print(f"Generated DOT files in {dot_dir}. You can convert them to images using Graphviz.")

    def analyze_repository(self):
        """Полный анализ репозитория с визуализацией"""
        groups, file_details = self.group_files_by_dependencies()
        self.generate_visualization(groups, file_details)
        
        self._generate_summary_report(groups, file_details)
        
        return groups, file_details

    def _generate_summary_report(self, groups: List[Set[str]], file_details: Dict[str, Dict]):
        """Генерирует сводный отчет по всему репозиторию"""
        report_path = os.path.join(self.repo_path, "_dependency_reports", "summary_report.txt")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=== Repository Dependency Analysis Summary ===\n\n")
            f.write(f"Total files analyzed: {sum(len(group) for group in groups)}\n")
            f.write(f"Total dependency groups: {len(groups)}\n\n")
            
            lang_stats = defaultdict(int)
            for details in file_details.values():
                lang = details.get("language", "Unknown")
                lang_stats[lang] += 1
            
            f.write("Language statistics:\n")
            for lang, count in sorted(lang_stats.items(), key=lambda x: -x[1]):
                f.write(f"- {lang}: {count} files\n")
            
            f.write("\nDependency groups:\n")
            for i, group in enumerate(groups, 1):
                f.write(f"\nGroup {i} ({len(group)} files):\n")
                langs_in_group = defaultdict(int)
                for file_path in group:
                    lang = file_details.get(file_path, {}).get("language", "Unknown")
                    langs_in_group[lang] += 1
                
                for lang, count in sorted(langs_in_group.items(), key=lambda x: -x[1]):
                    f.write(f"- {lang}: {count} files\n")
            
            all_files = [file for group in groups for file in group]
            top_files = sorted(all_files, key=lambda x: -file_details.get(x, {}).get("size", 0))[:10]
            
            f.write("\nTop 10 largest files:\n")
            for file in top_files:
                size = file_details.get(file, {}).get("size", 0)
                lang = file_details.get(file, {}).get("language", "Unknown")
                f.write(f"- {file} ({lang}, {size} bytes)\n")
            
            top_deps = sorted(all_files, key=lambda x: -len(file_details.get(x, {}).get("imports", [])))[:10]
            
            f.write("\nTop 10 files with most dependencies:\n")
            for file in top_deps:
                deps = len(file_details.get(file, {}).get("imports", []))
                lang = file_details.get(file, {}).get("language", "Unknown")
                f.write(f"- {file} ({lang}, {deps} dependencies)\n")

