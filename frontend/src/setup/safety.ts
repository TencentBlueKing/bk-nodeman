import NmRSA from './RSA';
import NmSM2 from './SM2';
import { ISafetyOption, ISafetyType } from '@/types';

const encryptList: ISafetyType[] = ['RSA', 'SM2'];

export declare class NmSafety {
  updateInstance(option: ISafetyOption): void;
  getInstance(): NmRSA | NmSM2;
  encrypt(val: string): string;
  decrypt(val: string): string;
}

export default class NmSafety {
  private instance: NmRSA | NmSM2;
  private type: ISafetyType;
  private name: string;
  private publicKey: string;
  private privateKey: string;

  private constructor(option: ISafetyOption = {}) {
    this.updateInstance(option);
  }

  public getInstance() {
    return this.instance;
  }

  public updateInstance(option: ISafetyOption = {}) {
    this.publicKey = option.publicKey || '';
    this.privateKey = option.privateKey || '';
    this.name = option.name || '';
    this.type = (!option.type || !encryptList.includes(option.type)) ? 'RSA' : option.type;

    const assOption = Object({ ...this }, option);
    switch (this.type)  {
      case 'RSA':
        this.instance = new NmRSA(assOption);
        break;
      case 'SM2':
        this.instance = new NmSM2(assOption);
        break;
    }
  }

  public encrypt(val: string) {
    const encryptBase64 = this.instance?.defaultEncrypt(val) || '';
    return encryptBase64 ? `${btoa(this.name)}${encryptBase64}` : '';
  }
  public decrypt(val: string) {
    // 需要去除 btoa(this.name) 前缀部分
    return this.instance?.defaultDecrypt(val);
  }
}
