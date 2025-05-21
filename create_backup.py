import os
import zipfile
from datetime import datetime

def create_backup():
    # Définir le nom du fichier ZIP avec la date
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"backup_{timestamp}.zip"
    
    # Obtenir le chemin absolu du dossier courant
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Liste des fichiers à exclure
    exclude = {
        '__pycache__',
        'venv',
        '.git',
        'backup_',  # Pour exclure les anciens backups
        zip_name    # Pour exclure le fichier ZIP en cours de création
    }
    
    print(f"Création du backup : {zip_name}")
    
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Parcourir tous les fichiers du dossier
            for root, dirs, files in os.walk(current_dir):
                # Filtrer les dossiers à exclure
                dirs[:] = [d for d in dirs if d not in exclude]
                
                for file in files:
                    # Vérifier si le fichier doit être exclu
                    if any(ex in file for ex in exclude):
                        continue
                        
                    file_path = os.path.join(root, file)
                    # Calculer le chemin relatif pour le ZIP
                    rel_path = os.path.relpath(file_path, current_dir)
                    
                    print(f"Ajout : {rel_path}")
                    zipf.write(file_path, rel_path)
        
        print(f"\nBackup créé avec succès : {zip_name}")
        print(f"Taille du fichier : {os.path.getsize(zip_name) / (1024*1024):.2f} MB")
        
    except Exception as e:
        print(f"Erreur lors de la création du backup : {str(e)}")

if __name__ == "__main__":
    create_backup()
