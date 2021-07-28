type PromiseFn = (...params: any) => Promise<any>;
/**
 * 顺序执行Promise，并返回结果
 * @param {Array} promises 每项为函数，返回值为数组
 * @param {Object} args 参数
 */
function primiseSequence(promises: PromiseFn[], args: any) {
  const p = Promise.resolve();
  const len = promises.length;
  let i = 0;

  if (len <= 0) {
    return p;
  }

  function callBack(...params: any): any {
    return p.then(r => promises[i](r, ...params)).then((r) => {
      i = i + 1;
      return i > len - 1 ? Promise.resolve(r) : callBack(...params);
    });
  }

  return callBack(args);
}

export default primiseSequence;
