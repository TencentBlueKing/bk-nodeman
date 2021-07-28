import open from 'open'
import webpack from 'webpack'
import ora from 'ora'
import url from 'url'

import devConf from './webpack.dev.conf'
import config from './config'
import checkVer from './check-versions'
import WebpackDevServer from 'webpack-dev-server'

const spinner = ora('> Starting dev server... \n').start()

checkVer()

const compiler = webpack(devConf)

const port = process.env.PORT || config.dev.localDevPort
const host = config.dev.localDevUrl || '127.0.0.1'
const urlParse = url.parse(`${host}:${port}`)

const server = new WebpackDevServer(compiler, {
    host: urlParse.hostname || '',
    port,
    proxy: config.dev.proxyTable,
    hot: true,
    publicPath: devConf.output?.publicPath as string,
    open: false,
    stats: {
      assets: false,
      moduleAssets: false,
      chunkRelations: false,
      colors: true,
      logging: 'none'
    },
    watchContentBase: false,
    disableHostCheck: true
})

compiler.hooks.invalid.tap('invalid', () => {
    console.log('Compiling...')
})

compiler.hooks.done.tap('done', () => {
    console.log(`> Listening at ${urlParse.href}\n`)
})

server.listen(port, '127.0.0.1', (err) => {
    err && console.log(err) && process.exit(1)
    
    if (!!config.dev.autoOpenBrowser) {
        open(urlParse.href)
    }
    spinner.stop()
})