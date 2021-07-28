import path from 'path'

export function resolve (dir: string) {
    return path.join(__dirname, '..', dir)
}

export function assetsPath (_path: string) {
    const assetsSubDirectory = 'nodeman'
    return path.posix.join(assetsSubDirectory, _path)
}
