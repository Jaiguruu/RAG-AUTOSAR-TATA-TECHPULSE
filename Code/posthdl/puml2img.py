import os
import shutil
import subprocess

def generate_plantuml_image(uml_file_path: str, output_image_path: str) -> None:
    """Generate PNG image from PlantUML file using plantuml JAR."""
    plantuml_jar_path = "plantuml-1.2024.7.jar"
    if not os.path.exists(plantuml_jar_path):
        return

    subprocess.run(["java", "-jar", plantuml_jar_path, uml_file_path], check=False)

    generated_image_path = uml_file_path.replace(".puml", ".png")
    if os.path.exists(generated_image_path):
        shutil.move(generated_image_path, output_image_path)
