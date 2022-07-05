import { request } from '../base';

export const toolsDownload = request('GET', 'tools/download/');

export default {
  toolsDownload,
};
