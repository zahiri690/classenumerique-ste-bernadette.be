import random
import string
from typing import List, Tuple, Dict, Optional
import numpy as np

class WordSearchGenerator:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid = [[' ' for _ in range(width)] for _ in range(height)]
        self.words = []
        self.word_positions = {}  # Pour stocker les positions des mots

    def can_place_word(self, word: str, x: int, y: int, dx: int, dy: int) -> bool:
        """Vérifie si un mot peut être placé à une position donnée dans une direction donnée."""
        if len(word) > self.width and dx != 0:
            return False
        if len(word) > self.height and dy != 0:
            return False

        curr_x, curr_y = x, y
        for letter in word:
            if (curr_x < 0 or curr_x >= self.width or 
                curr_y < 0 or curr_y >= self.height):
                return False
            
            if self.grid[curr_y][curr_x] != ' ' and self.grid[curr_y][curr_x] != letter:
                return False
            
            curr_x += dx
            curr_y += dy
        
        return True

    def place_word(self, word: str, x: int, y: int, dx: int, dy: int) -> None:
        """Place un mot dans la grille à une position donnée dans une direction donnée."""
        positions = []
        curr_x, curr_y = x, y
        for letter in word:
            self.grid[curr_y][curr_x] = letter
            positions.append((curr_x, curr_y))
            curr_x += dx
            curr_y += dy
        self.word_positions[word] = positions

    def add_word(self, word: str) -> bool:
        """Tente d'ajouter un mot dans la grille."""
        word = word.upper()
        if word in self.words:
            return False

        # Directions possibles (horizontale, verticale, diagonale)
        directions = [
            (1, 0),   # droite
            (0, 1),   # bas
            (1, 1),   # diagonale bas-droite
            (-1, 1),  # diagonale bas-gauche
        ]

        # Essayer plusieurs positions aléatoires
        attempts = 100
        while attempts > 0:
            dx, dy = random.choice(directions)
            if random.random() < 0.5:  # 50% de chance d'inverser le mot
                word = word[::-1]
            
            # Calculer les limites pour le placement
            x_limit = self.width - len(word) + 1 if dx > 0 else self.width
            y_limit = self.height - len(word) + 1 if dy > 0 else self.height
            
            x = random.randint(0, x_limit - 1)
            y = random.randint(0, y_limit - 1)

            if self.can_place_word(word, x, y, dx, dy):
                self.place_word(word, x, y, dx, dy)
                self.words.append(word)
                return True
            
            attempts -= 1
        
        return False

    def fill_empty(self) -> None:
        """Remplit les cases vides avec des lettres aléatoires."""
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == ' ':
                    self.grid[y][x] = random.choice(string.ascii_uppercase)

    def get_grid(self) -> List[List[str]]:
        """Retourne la grille actuelle."""
        return self.grid

    def get_words(self) -> List[str]:
        """Retourne la liste des mots placés."""
        return self.words

    def get_word_positions(self) -> Dict[str, List[Tuple[int, int]]]:
        """Retourne les positions des mots dans la grille."""
        return self.word_positions

def generate_word_search(words: List[str], width: int = 15, height: int = 15) -> Optional[Dict]:
    """Génère une grille de mots mêlés avec les mots donnés."""
    # Vérifier les dimensions minimales
    if width < 5 or height < 5:
        return None
    if not words:
        return None

    # Trier les mots par longueur (plus longs en premier)
    words = sorted(words, key=len, reverse=True)
    
    # Créer la grille
    generator = WordSearchGenerator(width, height)
    
    # Essayer de placer chaque mot
    placed_words = []
    for word in words:
        if generator.add_word(word.strip()):
            placed_words.append(word.upper())
    
    # Si aucun mot n'a pu être placé, retourner None
    if not placed_words:
        return None
    
    # Remplir les espaces vides
    generator.fill_empty()
    
    return {
        'grid': generator.get_grid(),
        'words': placed_words,
        'word_positions': generator.get_word_positions()
    }
