import { extname } from 'path'
import { Compiler } from 'webpack'

export default class ReplaceCSSStaticUrlPlugin {
    apply (compiler: Compiler) {
        // emit: 在生成资源并输出到目录之前
        compiler.hooks.emit.tap('ReplaceCSSStaticUrlPlugin', (compilation) => {
            const assets = Object.keys(compilation.assets)
            const assetsLen = assets.length
            for (let i = 0; i < assetsLen; i++) {
                const fileName = assets[i]
                if (extname(fileName) !== '.css' && fileName !== 'index.html') {
                    continue
                }

                const asset = compilation.assets[fileName]

                let minifyFileContent = ''
                if (fileName === 'index.html') {
                    minifyFileContent = asset.source().toString().replace(
                        /\{\{\s*STATIC_URL\s*\}\}\/nodeman/g,
                        () => '{{STATIC_URL}}nodeman'
                    )
                } else {
                    minifyFileContent = asset.source().toString().replace(
                        /\{\{\s*STATIC_URL\s*\}\}/g,
                        () => '../../'
                    )
                }
                // 设置输出资源
                const newAssets: any = {
                    // 返回文件内容
                    source: () => minifyFileContent,
                    // 返回文件大小
                    size: () => Buffer.byteLength(minifyFileContent, 'utf8')
                }
                compilation.updateAsset(fileName, newAssets)
                // if (fileName === 'index.html') {
                //   Object.assign(asset, {
                //       // 返回文件内容
                //       source: () => minifyFileContent,
                //       // 返回文件大小
                //       size: () => Buffer.byteLength(minifyFileContent, 'utf8')
                //   })
                //   compilation.updateAsset(fileName, asset)
                // }
            }
        })
    }
}
