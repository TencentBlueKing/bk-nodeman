import cryptoJsSdk from '@blueking/crypto-js-sdk';
import SM2 from '@blueking/crypto-js-sdk/dist/sm2';
import { ISafetyOption } from '@/types';

export declare class ISM2 {
  private publicKey: string;
  private privateKey: string;
  private instance: SM2;
  public getPublicKey(val: string): string
  public getPrivateKey(val: string): string
  public defaultEncrypt(val: string): string
  public defaultDecrypt(val: string): string
}

/**
 * 国密
 */
export default class NmSM2 {
  private publicKey: string; // 获取实际的公钥，类型为 hex 字符串
  private privateKey: string;
  private instance: SM2;

  protected constructor(option: ISafetyOption) {
    const { publicKey = '', privateKey = '' } = option;
    this.instance = new cryptoJsSdk.SM2();
    this.publicKey = publicKey ? this.getPublicKey(publicKey) : '';
    this.privateKey = privateKey ? this.getPrivateKey(privateKey) : '';
  }

  // 蓝鲸的公钥私钥均使用了 asn1 der 编码，因此需要用此方法处理，得到实际的公私钥
  // 后续此方法会加入到 sdk 中
  public getPublicKey(pKey: string) {
    const publicKeyPem = cryptoJsSdk.helper.parseBlockPEM(pKey);
    const publicKeyJson = cryptoJsSdk.helper.asn1.parse(publicKeyPem.der);
    function loop(source: any) {
      const ret: any = [];
      const dfs = (data: any) => {
        if (data.type === 0x03) {
          ret.push(data);
        }
        if (data.children) {
          for (let i = 0; i < data.children.length; i++) {
            dfs(data.children[i]);
          }
        }
      };
      dfs(source);
      return ret;
    }
    const { value } = loop(publicKeyJson)[0];
    return cryptoJsSdk.helper.encode.bufToHex(value.data || value);
  }
  // 后续此方法会加入到 sdk 中
  public getPrivateKey(pKey: string) {
    const privateKeyPem = cryptoJsSdk.helper.parseBlockPEM(pKey);
    const privateKeyJson = cryptoJsSdk.helper.asn1.parse(privateKeyPem.der);

    function privateKeyLoop(source: any) {
      let ret = '';
      for (const i of source.children) {
        if (i.type === 0x04) {
          ret = ret + cryptoJsSdk.helper.encode.bufToHex(i.value);
        }
      }
      return ret;
    }
    const privateKeyHex = privateKeyLoop(privateKeyJson);
    return privateKeyHex;
  }

  // SM2 加密
  public defaultEncrypt(val: string): string {
    if (!this.publicKey) {
      console.error('Public key cannot be empty.');
      return '';
    }
    // 加密 api 的两个参数，分别为公钥以及需要加密的数据，类型均为 hex 字符串，返回的类型也是 hex 字符串
    const cipher = this.instance.encrypt(this.publicKey, cryptoJsSdk.helper.encode.strToHex(val));
    // 传输给后端需要 base64，因此使用 sdk 提供的方法将加密后的数据（hex 类型）转换为 base64
    const base64Ret = cryptoJsSdk.helper.encode.hexToBase64(cipher);
    // console.log(val, base64Ret, val === this.defaultDecrypt(base64Ret), 'SM2'); // test
    return base64Ret;
  }
  // SM2 解密
  public defaultDecrypt(val: string) { // hex 字符串
    if (!this.privateKey) {
      console.error('Private key cannot be empty.');
      return '';
    }
    const hexStr = this.instance.decrypt(this.privateKey, cryptoJsSdk.helper.encode.base64ToHex(val));
    // 解密 api 返回的数据类型为 hex 字符串，因此使用 sdk 提供的方法将 hex 字符串转为普通字符串
    const decryptRes = cryptoJsSdk.helper.encode.hexToStr(hexStr);
    // console.log(hexStr, decryptRes);
    return decryptRes;
  }
}
