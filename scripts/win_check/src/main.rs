// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
// Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.
use std::process::Command;
extern crate clap;
use clap::{Arg,App};

struct Message {
    service_short_name: [String; 5],
    service_display_name: [String; 5],
    port: [i32; 4]
}

fn main() {
    let message = Message {
        service_short_name: ["SSDPSRV".to_string(), "upnphost".to_string(), "LanmanServer".to_string(), "Netlogon".to_string(), "lmhosts".to_string()],
        service_display_name:  ["SSDP Discovery".to_string(), "UPnP Device Host".to_string(), "Server".to_string(), "NetLogon".to_string(), "TCP/IP NetBIOS Helper".to_string()],
        port: [135, 139, 445, 65534], // 需要开启一个高位端口，本身是随机的，不好解释，直接写死
    };
    let matches = App::new("windows check")
                          .version("1.0")
                          .about("BlueKing windows agent install related services and enable firewall port policy!")
                          .arg(
                              Arg::with_name("start")
                              .long("start")
                              .required(true)
                              .short("s")
                              .takes_value(true)
                              .help("example: '-s port'"))
                           .get_matches();


    let result =  matches.value_of("start"); 
    match result {
        Some(f) => {
            if f == "port" {
                for index in 0..message.port.len() {
                    check_firewall(message.port[index])
                }
            };
            if f == "service" {
                for index in 0..message.service_short_name.len() {
                    start_services(&message.service_short_name[index], &message.service_display_name[index]);

                }
            } else {
                println!("args : {} not support", f);
            }
        }
        None => println!("")
    }
}

fn start_services (service: &String, name: &String) {
    // 启动对应服务，这里有个未解决问题：通过sc query查询到的服务状态返回码是错的，而且返回是ansi的编码，难处理
    // 所以目前不做服务当前状态校验，直接启动
    println!("DEBUG: execute command: [{}]", format!("net start {}", service));
    let start_result = Command::new("cmd")
            .arg("/C")
            .arg("net start")
            .arg(service)
            .output()
            .expect("failed to start running service");
    match start_result.status.code() {
        Some(f) => {
            println!("code: {}", f);
            if f == 2 {
                // 已经启动的服务再次启动返回码为2
                log_info(format!("service {} is running", name));
            } else if f == 0 {
                log_info(format!("service {} start success", name));
            }else {
                log_err(format!("service {} start failed", name))
            }
        }
        None => println!("return code not found")
    }
}

fn log_info (log: String) {
    println!("INFO: {}", log);
}

fn log_err (log: String) {
    println!("ERROR: {}", log);
}

fn port_firewall_enable(port: i32) {
    let firewall_enable_command = format!("netsh advfirewall firewall add rule name= \"Open Port {}\" dir=in action=allow", port);
    println!("DEBUG: execute command: [{}]", firewall_enable_command);
    let start_result = Command::new("cmd")
            .arg("/C")
            .arg(firewall_enable_command)
            .output()
            .expect("failed to start running service");
    match start_result.status.code() {
        Some(f) => {
            if f == 0 {
                log_info(format!("port {} start success", port));
            }else {
                log_err(format!("port {} start failed", port))
            }
        }
        None => println!("return code not found")
    }
}

fn check_firewall(port: i32) {
    // 检测防火墙策略，如果没有则直接开启
    let per_command = format!("netsh advfirewall firewall show rule name= \"Open Port {}\" dir=in", port);
    println!("DEBUG: execute command: [{}]", per_command);
    let start_result = Command::new("cmd")
            .arg("/C")
            .arg(per_command)
            .output()
            .expect("failed to start running service");
    match start_result.status.code() {
        Some(f) => {
            if f == 0 {
                log_info(format!("port {} firewall has opened", port));
            }else {
                port_firewall_enable(port);
            }
        }
        None => println!("return code not found")
    }
}