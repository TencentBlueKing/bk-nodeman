import Vue from 'vue';
import EncryptJS  from 'jsencrypt';

class EncryptRSA {
  private instance = null;
  private publicKey = '';
  public constructor() {
    this.instance = new EncryptJS();
    this.publicKey = '';
  }

  public setPublicKey(publicKey: string) {
    this.publicKey = publicKey;
    this.instance.setPublicKey(publicKey);
  }
  public get(word: string, publicKey?: string): string {
    if (publicKey && typeof publicKey === 'string') {
      this.setPublicKey(publicKey);
    }
    if (!this.publicKey) {
      console.warn('The public key is empty!');
      return '';
    }
    return this.instance.encrypt(word);
  }
}

export const RSA = new EncryptRSA();

Vue.prototype.$RSA = RSA;
