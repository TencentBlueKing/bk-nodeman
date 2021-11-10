import { request } from '../base';

export const collectJobLog = request('POST', 'api/job/{{pk}}/collect_log/');
export const getJobCommands = request('GET', 'api/job/{{pk}}/get_job_commands/');
export const getJobLog = request('GET', 'api/job/{{pk}}/log/');
export const installJob = request('POST', 'api/job/install/');
export const listJob = request('POST', 'api/job/job_list/');
export const operateJob = request('POST', 'api/job/operate/');
export const retrieveJob = request('POST', 'api/job/{{pk}}/details/');
export const retryJob = request('POST', 'api/job/{{pk}}/retry/');
export const retryNode = request('POST', 'api/job/{{pk}}/retry_node/');
export const revokeJob = request('POST', 'api/job/{{pk}}/revoke/');

export default {
  collectJobLog,
  getJobCommands,
  getJobLog,
  installJob,
  listJob,
  operateJob,
  retrieveJob,
  retryJob,
  retryNode,
  revokeJob,
};
