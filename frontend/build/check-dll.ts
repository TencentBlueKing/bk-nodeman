import path from 'path'
import fse from 'fs-extra'
import npm from 'npm'

const manifestExist = fse.pathExistsSync(path.resolve(__dirname, '..', 'static', 'lib-manifest.json'))
const bundleExist = fse.pathExistsSync(path.resolve(__dirname, '..', 'static', 'lib.bundle.js'))

if (!(manifestExist && bundleExist)) {
    npm.load({}, () => {
        npm.commands["run-script"](['dll'], (err) => {
          if (err) {
              throw err
          }
        })
    })
}
