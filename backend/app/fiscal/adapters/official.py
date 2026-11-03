from app.fiscal.adapters.base import FiscalAdapter


class NfseNacionalAdapter(FiscalAdapter):
    """Contrato para implementação futura após documentação e homologação oficiais."""
    def emitir_nota(self, *args, **kwargs):
        raise NotImplementedError("Transmissão oficial indisponível na v0.1.0")
    def consultar_nota(self, *args, **kwargs):
        raise NotImplementedError("Consulta oficial indisponível")
    def cancelar_nota(self, *args, **kwargs):
        raise NotImplementedError("Cancelamento oficial indisponível")
    def obter_documento(self, *args, **kwargs):
        raise NotImplementedError("Documentos oficiais indisponíveis")
    def verificar_conexao(self):
        return {"connected": False, "message": "Integração oficial não implementada"}


class NfseMunicipalAdapter(NfseNacionalAdapter):
    pass
