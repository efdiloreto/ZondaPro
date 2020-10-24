class PresionesMixin:
    def aumentar_escala_flechas(self):
        """Aumentar la escala de las flechas para todos los actores de presón."""
        for actor in self._actores_presion:
            actor.flecha.aumentar_escala()
        self.interactor.ReInitialize()

    def disminuir_escala_flechas(self):
        """Disminuye la escala de las flechas para todos los actores de presón."""
        for actor in self._actores_presion:
            actor.flecha.disminuir_escala()
        self.interactor.ReInitialize()

    def aumentar_tamanio_label_presion(self):
        """Aumenta los tamaños de textos en los actores de presión."""
        for actor in self._actores_presion:
            actor.flecha.label.aumentar_tamaño()
        self.interactor.ReInitialize()

    def disminuir_tamanio_label_presion(self):
        """Disminuye los tamaños de textos en los actores de presión."""
        for actor in self._actores_presion:
            actor.flecha.label.disminuir_tamaño()
        self.interactor.ReInitialize()

    def ocultar_actores_presion(self):
        """Oculta los actores de presión en el renderer"""
        for actor in self._actores_presion:
            actor.ocultar()
