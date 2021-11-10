import path from 'path'
import prodEnv from './prod.env'
import devEnv, { targetSiteUrl, proxyTableTarget } from './dev.env'

export default {
    build: {
        // env 会通过 webpack.DefinePlugin 注入到前端代码里
        env: prodEnv,
        assetsRoot: path.resolve(__dirname, '../../static'),
        assetsSubDirectory: 'nodeman',
        assetsPublicPath: '{{STATIC_URL}}',
        productionSourceMap: true,
        productionGzip: false,
        productionGzipExtensions: ['js', 'css'],
        bundleAnalyzerReport: process.env.npm_config_report
    },
    dev: {
        // env 会通过 webpack.DefinePlugin 注入到前端代码里
        env: devEnv,
        assetsRoot: '',
        // 这里用 JSON.parse 是因为 dev.env.js 里有一次 JSON.stringify，dev.env.js 里的 JSON.stringify 不能去掉
        localDevUrl: JSON.parse(devEnv.LOCAL_DEV_URL),
        localDevPort: JSON.parse(devEnv.LOCAL_DEV_PORT),
        assetsSubDirectory: 'static',
        assetsPublicPath: '/',
        proxyTable: {
            '/api': {
                target: `${proxyTableTarget}${targetSiteUrl}`, // 接口域名
                changeOrigin: true, // 是否跨域
                secure: false,
                toProxy: true,
                headers: {
                  referer: proxyTableTarget
                }
            },
            '/core/api': {
                target: `${proxyTableTarget}${targetSiteUrl}`,
                changeOrigin: true,
                secure: false,
                toProxy: true,
                headers: {
                  referer: proxyTableTarget
                }
            },
            '/backend/api': {
                target: `${proxyTableTarget}${targetSiteUrl}`,
                changeOrigin: true,
                secure: false,
                toProxy: true,
                headers: {
                  referer: proxyTableTarget
                }
            },
            '/download': {
                target: `${proxyTableTarget}${targetSiteUrl}/static`,
                changeOrigin: true,
                secure: false,
                toProxy: true,
                headers: {
                  referer: proxyTableTarget
                }
            },
            '/version_log': {
                target: `${proxyTableTarget}${targetSiteUrl}`,
                changeOrigin: true,
                secure: false,
                toProxy: true
            }
        },
        cssSourceMap: false,
        autoOpenBrowser: true
    }
}