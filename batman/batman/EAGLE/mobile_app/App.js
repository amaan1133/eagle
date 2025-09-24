;b 
import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  SafeAreaView,
  StatusBar,
} from 'react-native';

const API_BASE_URL = 'https://your-repl-name-username.replit.app';

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loginForm, setLoginForm] = useState({
    username: '',
    password: '',
    company_id: ''
  });

  useEffect(() => {
    fetchCompanies();
  }, []);

  useEffect(() => {
    if (isLoggedIn) {
      fetchTasks();
    }
  }, [isLoggedIn]);

  const fetchCompanies = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/companies`);
      const data = await response.json();
      setCompanies(data);
    } catch (error) {
      console.error('Error fetching companies:', error);
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/tasks`, {
        credentials: 'include',
      });
      const data = await response.json();
      setTasks(data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
    }
  };

  const handleLogin = async () => {
    if (!loginForm.username || !loginForm.password || !loginForm.company_id) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(loginForm),
      });

      const data = await response.json();

      if (data.success) {
        setUser(data.user);
        setIsLoggedIn(true);
        Alert.alert('Success', 'Login successful!');
      } else {
        Alert.alert('Error', data.message || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      Alert.alert('Error', 'Network error occurred');
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUser(null);
    setTasks([]);
    setLoginForm({ username: '', password: '', company_id: '' });
  };

  const updateTaskStatus = async (taskId, newStatus) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/update_task_status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          task_id: taskId,
          status: newStatus,
        }),
      });

      const data = await response.json();

      if (data.success) {
        fetchTasks();
        Alert.alert('Success', 'Task status updated!');
      } else {
        Alert.alert('Error', 'Failed to update task status');
      }
    } catch (error) {
      console.error('Error updating task:', error);
      Alert.alert('Error', 'Network error occurred');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'Completed':
        return '#28a745';
      case 'In Progress':
        return '#007bff';
      case 'Pending':
        return '#ffc107';
      default:
        return '#6c757d';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'Critical':
        return '#dc3545';
      case 'High':
        return '#fd7e14';
      case 'Medium':
        return '#ffc107';
      case 'Low':
        return '#28a745';
      default:
        return '#6c757d';
    }
  };

  if (!isLoggedIn) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar backgroundColor="#343a40" barStyle="light-content" />
        <View style={styles.loginContainer}>
          <Text style={styles.title}>🦅 Eagle Task Manager</Text>
          
          <View style={styles.formGroup}>
            <Text style={styles.label}>Username/Mobile:</Text>
            <TextInput
              style={styles.input}
              value={loginForm.username}
              onChangeText={(text) => setLoginForm({...loginForm, username: text})}
              placeholder="Enter username or mobile number"
              autoCapitalize="none"
            />
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Password:</Text>
            <TextInput
              style={styles.input}
              value={loginForm.password}
              onChangeText={(text) => setLoginForm({...loginForm, password: text})}
              placeholder="Enter password"
              secureTextEntry
            />
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Company:</Text>
            <ScrollView style={styles.companyList}>
              {companies.map((company) => (
                <TouchableOpacity
                  key={company.id}
                  style={[
                    styles.companyItem,
                    loginForm.company_id === company.id.toString() && styles.selectedCompany
                  ]}
                  onPress={() => setLoginForm({...loginForm, company_id: company.id.toString()})}
                >
                  <Text style={[
                    styles.companyText,
                    loginForm.company_id === company.id.toString() && styles.selectedCompanyText
                  ]}>
                    {company.name}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>

          <TouchableOpacity style={styles.loginButton} onPress={handleLogin}>
            <Text style={styles.loginButtonText}>Login</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar backgroundColor="#343a40" barStyle="light-content" />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Welcome, {user?.username}</Text>
        <Text style={styles.headerSubtitle}>Role: {user?.role}</Text>
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Text style={styles.logoutButtonText}>Logout</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.tasksContainer}>
        <Text style={styles.sectionTitle}>My Tasks ({tasks.length})</Text>
        
        {tasks.length === 0 ? (
          <View style={styles.noTasks}>
            <Text style={styles.noTasksText}>No tasks assigned</Text>
          </View>
        ) : (
          tasks.map((task) => (
            <View key={task.id} style={styles.taskCard}>
              <View style={styles.taskHeader}>
                <Text style={styles.taskTitle}>{task.title}</Text>
                <View style={[styles.priorityBadge, { backgroundColor: getPriorityColor(task.priority) }]}>
                  <Text style={styles.priorityText}>{task.priority}</Text>
                </View>
              </View>
              
              <Text style={styles.taskDescription}>{task.description}</Text>
              
              <View style={styles.taskMeta}>
                <Text style={styles.taskDate}>Created: {new Date(task.created_at).toLocaleDateString()}</Text>
                {task.deadline && (
                  <Text style={styles.taskDeadline}>Deadline: {new Date(task.deadline).toLocaleDateString()}</Text>
                )}
              </View>

              <View style={styles.taskActions}>
                <View style={[styles.statusBadge, { backgroundColor: getStatusColor(task.status) }]}>
                  <Text style={styles.statusText}>{task.status}</Text>
                </View>
                
                {user?.role !== 'Admin' && (
                  <View style={styles.statusButtons}>
                    {task.status !== 'Pending' && (
                      <TouchableOpacity
                        style={[styles.statusButton, styles.pendingButton]}
                        onPress={() => updateTaskStatus(task.id, 'Pending')}
                      >
                        <Text style={styles.statusButtonText}>Pending</Text>
                      </TouchableOpacity>
                    )}
                    {task.status !== 'In Progress' && (
                      <TouchableOpacity
                        style={[styles.statusButton, styles.progressButton]}
                        onPress={() => updateTaskStatus(task.id, 'In Progress')}
                      >
                        <Text style={styles.statusButtonText}>In Progress</Text>
                      </TouchableOpacity>
                    )}
                    {task.status !== 'Completed' && (
                      <TouchableOpacity
                        style={[styles.statusButton, styles.completedButton]}
                        onPress={() => updateTaskStatus(task.id, 'Completed')}
                      >
                        <Text style={styles.statusButtonText}>Complete</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                )}
              </View>
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  loginContainer: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 40,
    color: '#343a40',
  },
  formGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#495057',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ced4da',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  companyList: {
    maxHeight: 150,
    borderWidth: 1,
    borderColor: '#ced4da',
    borderRadius: 8,
    backgroundColor: '#fff',
  },
  companyItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  selectedCompany: {
    backgroundColor: '#007bff',
  },
  companyText: {
    fontSize: 16,
    color: '#495057',
  },
  selectedCompanyText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  loginButton: {
    backgroundColor: '#007bff',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 20,
  },
  loginButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  header: {
    backgroundColor: '#343a40',
    padding: 20,
    alignItems: 'center',
  },
  headerTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  headerSubtitle: {
    color: '#adb5bd',
    fontSize: 14,
    marginTop: 4,
  },
  logoutButton: {
    backgroundColor: '#dc3545',
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 4,
    marginTop: 10,
  },
  logoutButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  tasksContainer: {
    flex: 1,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#343a40',
  },
  noTasks: {
    alignItems: 'center',
    marginTop: 50,
  },
  noTasksText: {
    fontSize: 16,
    color: '#6c757d',
  },
  taskCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  taskHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  taskTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#343a40',
    flex: 1,
    marginRight: 8,
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  priorityText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  taskDescription: {
    fontSize: 14,
    color: '#6c757d',
    marginBottom: 12,
    lineHeight: 20,
  },
  taskMeta: {
    marginBottom: 12,
  },
  taskDate: {
    fontSize: 12,
    color: '#6c757d',
    marginBottom: 2,
  },
  taskDeadline: {
    fontSize: 12,
    color: '#dc3545',
    fontWeight: 'bold',
  },
  taskActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  statusText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  statusButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  statusButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  pendingButton: {
    backgroundColor: '#ffc107',
  },
  progressButton: {
    backgroundColor: '#007bff',
  },
  completedButton: {
    backgroundColor: '#28a745',
  },
  statusButtonText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: 'bold',
  },
});
