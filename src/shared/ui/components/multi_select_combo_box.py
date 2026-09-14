MultiSelectComboBox
│
├── QComboBox
│
├── QStandardItemModel
│   ├── Item
│   │   ├── text
│   │   ├── value
│   │   └── checked
│   │
│   ├── Item
│   └── Item
│
└── comportamiento
    ├── añadir elementos
    ├── eliminar elementos
    ├── marcar/desmarcar
    ├── obtener seleccionados
    ├── limpiar selección
    └── actualizar texto mostrado



ejemplo de uso en ferlo, steriflow para el filtro de als mauqinas 

combo = MultiSelectComboBox()

combo.add_item("Autoclave 1", 1)
combo.add_item("Autoclave 2", 2)
combo.add_item("Autoclave 3", 3)

combo.set_selected_values([1, 3])

values = combo.selected_values()

api de ejempo 
class MultiSelectComboBox(QComboBox):

    def add_item(self, text, value=None):
        ...

    def add_items(self, items):
        ...

    def selected_values(self):
        ...

    def selected_items(self):
        ...

    def set_selected_values(self, values):
        ...

    def clear_selection(self):
        ...

    def select_all(self):
        ...

    def deselect_all(self):
        ...


    Separación importante

Yo no metería dentro del componente nada específico de autoclaves, programas, ciclos, etc.