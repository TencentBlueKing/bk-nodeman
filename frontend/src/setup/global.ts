// 全局函数
const topWindow = getTopWindow();
try {
  topWindow.BLUEKING.corefunc.open_login_dialog = openLoginDialog;
  topWindow.BLUEKING.corefunc.close_login_dialog = closeLoginDialog;
  console.log('弹窗方法已注册到TOP窗口', window.top.BLUEKING.corefunc.close_login_dialog);
} catch (_) {
  topWindow.BLUEKING = {
    corefunc: {
      open_login_dialog: openLoginDialog,
      close_login_dialog: closeLoginDialog,
    },
  };
  window.open_login_dialog = openLoginDialog;
  window.close_login_dialog = closeLoginDialog;
  console.log('弹窗方法已注册到当前窗口', window.close_login_dialog);
}
export function openLoginDialog() {
  window.LoginModal && (window.LoginModal.show());
}
export function closeLoginDialog() {
  try {
    window.LoginModal && (window.LoginModal.$data.visible = false);
    window.location.reload();
  } catch (err) {
    console.log(err);
  }
}

function getTopWindow() {
  try {
    if (window.top && window.top.document) {
      console.log('TOP窗口对象获取成功');
      return window.top;
    }
    console.log('TOP窗口对象获取失败，已切换到当前窗口对象');
    return window;
  } catch (err) {
    console.log(err);
    console.log('TOP窗口对象获取失败，已切换到当前窗口对象');
    return window;
  }
}
