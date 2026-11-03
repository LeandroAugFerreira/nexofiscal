"""Verifica SMTP com as credenciais locais. Nunca envia mensagem nem edita .env."""
import argparse
import json
import smtplib
import ssl
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connect", action="store_true", help="Testar TLS e autenticar, sem enviar e-mail.")
    parser.add_argument("--port", type=int, choices=(465, 587), help="Porta usada apenas nesta verificação.")
    parser.add_argument("--challenge-auth", action="store_true", help="Aguardar desafio SMTP antes de apresentar a autenticação.")
    parser.add_argument("--probe-auth", action="store_true", help="Solicitar desafio AUTH LOGIN sem apresentar usuário/senha, cancelar e encerrar.")
    parser.add_argument("--auth-method", choices=("auto", "login"), default="auto", help="Mecanismo de autenticação usado apenas neste diagnóstico.")
    args = parser.parse_args()
    # Settings usa caminhos relativos ao backend, como no startup normal da API.
    import os
    os.chdir(ROOT / "backend")
    from app.core.config import settings
    from app.services.email_delivery import configuration
    cfg = settings()
    port = args.port or cfg.smtp_port
    result = {
        "configured": configuration()["configured"],
        "host": cfg.smtp_host,
        "configured_port": cfg.smtp_port,
        "verification_port": port,
        "transport": "STARTTLS" if port == 587 else "TLS direto",
        "sender": cfg.smtp_from_email,
        "authentication_matches_sender": cfg.smtp_username == cfg.smtp_from_email,
        "configuration_modified": False,
        "email_sent": False,
        "challenge_auth": args.challenge_auth,
        "credentials_sent": False,
        "auth_method": args.auth_method,
    }
    if not args.connect:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not result["configured"] or cfg.smtp_host != "smtp.gmail.com":
        result["error"] = "Configuração incompleta ou host diferente do Gmail. Nenhuma conexão iniciada."
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    connection = None
    stage = "conexão"
    try:
        context = ssl.create_default_context()
        if port == 587:
            connection = smtplib.SMTP(cfg.smtp_host, port, timeout=15)
            connection.ehlo()
            stage = "STARTTLS"
            connection.starttls(context=context)
            stage = "EHLO após TLS"
            connection.ehlo()
        else:
            connection = smtplib.SMTP_SSL(cfg.smtp_host, port, timeout=15, context=context)
            connection.ehlo()
        result["tls"] = connection.sock.version()
        result["certificate_validation"] = context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        peer = connection.sock.getpeercert()
        result["certificate_issuer"] = [value for item in peer.get("issuer", ()) for key, value in item
            if key in ("organizationName", "commonName")]
        result["noop_before_auth"] = connection.noop()[0]
        if args.probe_auth:
            stage = "desafio AUTH LOGIN sem credenciais"
            code, _ = connection.docmd("AUTH", "LOGIN")
            result["auth_challenge_code"] = code
            if code == 334:
                result["auth_cancel_code"] = connection.docmd("*")[0]
                result["probe_completed"] = True
            else:
                result["probe_completed"] = False
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result.get("probe_completed") else 1
        stage = "autenticação"
        result["credentials_sent"] = True
        if args.auth_method == "login":
            connection.user = cfg.smtp_username
            connection.password = cfg.smtp_password
            connection.auth("LOGIN", connection.auth_login, initial_response_ok=False)
        else:
            connection.login(cfg.smtp_username, cfg.smtp_password, initial_response_ok=not args.challenge_auth)
        result["authenticated"] = True
        stage = "NOOP"
        result["noop_code"] = connection.noop()[0]
    except smtplib.SMTPAuthenticationError as error:
        result["authenticated"] = False
        result["server_code"] = error.smtp_code
        result["failed_stage"] = stage
        result["error"] = "Gmail recusou a autenticação. Verifique a conta e a senha de app localmente."
    except (ssl.SSLError, smtplib.SMTPException, OSError) as error:
        result["authenticated"] = False
        result["failed_stage"] = stage
        result["error_type"] = type(error).__name__
        code = getattr(error, "smtp_code", None)
        if isinstance(code, int):
            result["server_code"] = code
        result["error"] = "Não foi possível concluir a verificação SMTP. A resposta detalhada foi omitida para preservar credenciais."
    finally:
        if connection is not None:
            try:
                connection.quit()
            except (smtplib.SMTPException, OSError):
                pass
    # Nunca ativa debug SMTP, imprime respostas de AUTH ou chama MAIL/RCPT/DATA.
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("authenticated") else 1


if __name__ == "__main__":
    raise SystemExit(main())
