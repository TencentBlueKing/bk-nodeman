import base64

from django.conf import settings
from kubernetes import config
from kubernetes.client import Configuration, CoreV1Api, V1ObjectMeta, V1Secret, api_client, exceptions

from apigw_manager.apigw.helper import BasePublicKeyManager


class SecretPublicKeyManager(BasePublicKeyManager):
    def __init__(self):

        self.namespace = getattr(settings, "APIGW_JWT_PUBLIC_KEY_SECRET_NAMESPACE", "default")
        self.secret_mappings = getattr(settings, "APIGW_JWT_PUBLIC_KEY_SECRET_MAPPINGS", {})

        configuration = Configuration()
        config.load_incluster_config(configuration)
        self.client = CoreV1Api(api_client=api_client.ApiClient(configuration=configuration))

    def get(self, api_name, issuer=None):

        try:
            secret = self.client.read_namespaced_secret(self._get_name(issuer), self.namespace)
        except exceptions.ApiException as err:
            if err.status == 404:
                return None

            raise

        public_keys = getattr(secret, "data", None) or {}

        if api_name not in public_keys:
            return None

        value = public_keys[api_name]

        return base64.b64decode(value).decode()

    def set(self, api_name, public_key, issuer=None):

        name = self._get_name(issuer)
        secret = V1Secret(
            metadata=V1ObjectMeta(
                name=name,
                namespace=self.namespace,
                annotations={
                    "bkgateway/issuer": issuer or "",
                    "bkgateway/api_name": api_name,
                },
            ),
            kind="Secret",
            type="Opaque",
            string_data={api_name: public_key},
        )

        try:
            self.client.patch_namespaced_secret(name, self.namespace, secret)
        except exceptions.ApiException as err:
            if err.status == 404:
                self.client.create_namespaced_secret(self.namespace, secret)
            else:
                raise

    def _get_name(self, issuer):
        return self.secret_mappings[issuer or "APIGW"]
