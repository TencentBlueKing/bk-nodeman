import { request } from '../base';

export const collectJobLog = request('POST', 'job/{{pk}}/collect_log/');
export const getJobCommands = request('GET', 'job/{{pk}}/get_job_commands/');
export const getJobLog = request('GET', 'job/{{pk}}/log/');
export const installJob = request('POST', 'job/install/');
export const listJob = request('POST', 'job/job_list/');
export const operateJob = request('POST', 'job/operate/');
export const retrieveJob = request('POST', 'job/{{pk}}/details/');
export const retryJob = request('POST', 'job/{{pk}}/retry/');
export const retryNode = request('POST', 'job/{{pk}}/retry_node/');
export const revokeJob = request('POST', 'job/{{pk}}/revoke/');

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
