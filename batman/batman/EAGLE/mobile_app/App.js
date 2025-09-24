
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
  Modal,
} from 'react-native';
import * as SQLite from 'expo-sqlite';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Initialize local SQLite database
const db = SQLite.openDatabase('eagle_tasks.db');

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [users, setUsers] = useState([]);
  const [loginForm, setLoginForm] = useState({
    username: '',
    password: '',
    company_id: ''
  });
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    assigned_to: '',
    priority: 'Medium'
  });

  // Initialize database on app load
  useEffect(() => {
    initializeDatabase();
    loadStoredUser();
  }, []);

  // Load tasks when user logs in
  useEffect(() => {
    if (isLoggedIn && user) {
      loadTasks();
    }
  }, [isLoggedIn, user]);

  const initializeDatabase = () => {
    db.transaction(tx => {
      // Companies table
      tx.executeSql(
        `CREATE TABLE IF NOT EXISTS companies (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL UNIQUE
        );`
      );

      // Users table
      tx.executeSql(
        `CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE,
          password TEXT NOT NULL,
          role TEXT NOT NULL,
          company_id INTEGER,
          FOREIGN KEY (company_id) REFERENCES companies (id)
        );`
      );

      // Tasks table
      tx.executeSql(
        `CREATE TABLE IF NOT EXISTS tasks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          description TEXT,
          assigned_to INTEGER,
          company_id INTEGER,
          status TEXT DEFAULT 'Pending',
          priority TEXT DEFAULT 'Medium',
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (assigned_to) REFERENCES users (id),
          FOREIGN KEY (company_id) REFERENCES companies (id)
        );`
      );

      // Insert sample data
      tx.executeSql(
        `INSERT OR IGNORE INTO companies (id, name) VALUES (1, 'TechCorp');`
      );
      
      tx.executeSql(
        `INSERT OR IGNORE INTO users (id, username, password, role, company_id) 
         VALUES (1, 'admin', 'admin123', 'Admin', 1);`
      );

      tx.executeSql(
        `INSERT OR IGNORE INTO users (id, username, password, role, company_id) 
         VALUES (2, 'manager', 'manager123', 'Manager', 1);`
      );

      tx.executeSql(
        `INSERT OR IGNORE INTO users (id, username, password, role, company_id) 
         VALUES (3, 'employee', 'employee123', 'Employee', 1);`
      );

      // Load initial data
      loadCompanies();
    });
  };

  const loadStoredUser = async () => {
    try {
      const storedUser = await AsyncStorage.getItem('user');
      if (storedUser) {
        const userData = JSON.parse(storedUser);
        setUser(userData);
        setIsLoggedIn(true);
      }
    } catch (error) {
      console.log('No stored user found');
    }
  };

  const loadCompanies = () => {
    db.transaction(tx => {
      tx.executeSql(
        'SELECT * FROM companies',
        [],
        (_, { rows }) => {
          setCompanies(rows._array);
        },
        (_, error) => console.error('Error loading companies:', error)
      );
    });
  };

  const loadUsers = (companyId) => {
    db.transaction(tx => {
      tx.executeSql(
        'SELECT id, username, role FROM users WHERE company_id = ?',
        [companyId],
        (_, { rows }) => {
          setUsers(rows._array);
        },
        (_, error) => console.error('Error loading users:', error)
      );
    });
  };

  const loadTasks = () => {
    db.transaction(tx => {
      let query, params;
      
      if (user.role === 'Admin') {
        query = `SELECT t.*, u.username as assigned_to_name 
                 FROM tasks t 
                 LEFT JOIN users u ON t.assigned_to = u.id 
                 WHERE t.company_id = ? 
                 ORDER BY t.created_at DESC`;
        params = [user.company_id];
      } else {
        query = `SELECT t.*, u.username as assigned_to_name 
                 FROM tasks t 
                 LEFT JOIN users u ON t.assigned_to = u.id 
                 WHERE t.assigned_to = ? AND t.company_id = ? 
                 ORDER BY t.created_at DESC`;
        params = [user.id, user.company_id];
      }

      tx.executeSql(
        query,
        params,
        (_, { rows }) => {
          setTasks(rows._array);
        },
        (_, error) => console.error('Error loading tasks:', error)
      );
    });
  };

  const handleLogin = () => {
    if (!loginForm.username || !loginForm.password || !loginForm.company_id) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    db.transaction(tx => {
      tx.executeSql(
        'SELECT * FROM users WHERE username = ? AND password = ? AND company_id = ?',
        [loginForm.username, loginForm.password, parseInt(loginForm.company_id)],
        async (_, { rows }) => {
          if (rows.length > 0) {
            const userData = rows._array[0];
            setUser(userData);
            setIsLoggedIn(true);
            
            // Store user data locally
            await AsyncStorage.setItem('user', JSON.stringify(userData));
            
            // Load users for task assignment
            loadUsers(userData.company_id);
            
            Alert.alert('Success', 'Login successful!');
          } else {
            Alert.alert('Error', 'Invalid credentials');
          }
        },
        (_, error) => {
          console.error('Login error:', error);
          Alert.alert('Error', 'Login failed');
        }
      );
    });
  };

  const handleLogout = async () => {
    await AsyncStorage.removeItem('user');
    setIsLoggedIn(false);
    setUser(null);
    setTasks([]);
    setUsers([]);
    setLoginForm({ username: '', password: '', company_id: '' });
  };

  const createTask = () => {
    if (!newTask.title || !newTask.assigned_to) {
      Alert.alert('Error', 'Please fill in required fields');
      return;
    }

    db.transaction(tx => {
      tx.executeSql(
        'INSERT INTO tasks (title, description, assigned_to, company_id, priority) VALUES (?, ?, ?, ?, ?)',
        [newTask.title, newTask.description, parseInt(newTask.assigned_to), user.company_id, newTask.priority],
        (_, result) => {
          Alert.alert('Success', 'Task created successfully!');
          setShowTaskForm(false);
          setNewTask({ title: '', description: '', assigned_to: '', priority: 'Medium' });
          loadTasks();
        },
        (_, error) => {
          console.error('Error creating task:', error);
          Alert.alert('Error', 'Failed to create task');
        }
      );
    });
  };

  const updateTaskStatus = (taskId, newStatus) => {
    db.transaction(tx => {
      tx.executeSql(
        'UPDATE tasks SET status = ? WHERE id = ?',
        [newStatus, taskId],
        (_, result) => {
          Alert.alert('Success', 'Task status updated!');
          loadTasks();
        },
        (_, error) => {
          console.error('Error updating task:', error);
          Alert.alert('Error', 'Failed to update task status');
        }
      );
    });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'Completed': return '#28a745';
      case 'In Progress': return '#007bff';
      case 'Pending': return '#ffc107';
      default: return '#6c757d';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'Critical': return '#dc3545';
      case 'High': return '#fd7e14';
      case 'Medium': return '#ffc107';
      case 'Low': return '#28a745';
      default: return '#6c757d';
    }
  };

  if (!isLoggedIn) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar backgroundColor="#343a40" barStyle="light-content" />
        <View style={styles.loginContainer}>
          <Text style={styles.title}>🦅 Eagle Task Manager</Text>
          <Text style={styles.subtitle}>Offline Version</Text>
          
          <View style={styles.formGroup}>
            <Text style={styles.label}>Username:</Text>
            <TextInput
              style={styles.input}
              value={loginForm.username}
              onChangeText={(text) => setLoginForm({...loginForm, username: text})}
              placeholder="Enter username"
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

          <View style={styles.credentialsInfo}>
            <Text style={styles.credentialsTitle}>Demo Credentials:</Text>
            <Text style={styles.credentialsText}>Admin: admin / admin123</Text>
            <Text style={styles.credentialsText}>Manager: manager / manager123</Text>
            <Text style={styles.credentialsText}>Employee: employee / employee123</Text>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar backgroundColor="#343a40" barStyle="light-content" />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Welcome, {user?.username}</Text>
        <Text style={styles.headerSubtitle}>Role: {user?.role} | Offline Mode</Text>
        <View style={styles.headerButtons}>
          {user?.role === 'Admin' && (
            <TouchableOpacity 
              style={styles.createButton} 
              onPress={() => setShowTaskForm(true)}
            >
              <Text style={styles.createButtonText}>+ Task</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
            <Text style={styles.logoutButtonText}>Logout</Text>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView style={styles.tasksContainer}>
        <Text style={styles.sectionTitle}>
          {user?.role === 'Admin' ? 'All Tasks' : 'My Tasks'} ({tasks.length})
        </Text>
        
        {tasks.length === 0 ? (
          <View style={styles.noTasks}>
            <Text style={styles.noTasksText}>No tasks available</Text>
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
              
              {user?.role === 'Admin' && (
                <Text style={styles.taskAssignee}>Assigned to: {task.assigned_to_name}</Text>
              )}

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

      {/* Create Task Modal */}
      <Modal
        visible={showTaskForm}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setShowTaskForm(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Create New Task</Text>
            
            <TextInput
              style={styles.input}
              value={newTask.title}
              onChangeText={(text) => setNewTask({...newTask, title: text})}
              placeholder="Task Title"
            />
            
            <TextInput
              style={[styles.input, styles.textArea]}
              value={newTask.description}
              onChangeText={(text) => setNewTask({...newTask, description: text})}
              placeholder="Task Description"
              multiline={true}
              numberOfLines={3}
            />

            <View style={styles.pickerContainer}>
              <Text style={styles.label}>Assign to:</Text>
              <ScrollView style={styles.userList}>
                {users.map((userItem) => (
                  <TouchableOpacity
                    key={userItem.id}
                    style={[
                      styles.userItem,
                      newTask.assigned_to === userItem.id.toString() && styles.selectedUser
                    ]}
                    onPress={() => setNewTask({...newTask, assigned_to: userItem.id.toString()})}
                  >
                    <Text style={[
                      styles.userText,
                      newTask.assigned_to === userItem.id.toString() && styles.selectedUserText
                    ]}>
                      {userItem.username} ({userItem.role})
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>

            <View style={styles.priorityContainer}>
              <Text style={styles.label}>Priority:</Text>
              <View style={styles.priorityButtons}>
                {['Low', 'Medium', 'High', 'Critical'].map((priority) => (
                  <TouchableOpacity
                    key={priority}
                    style={[
                      styles.priorityButton,
                      newTask.priority === priority && styles.selectedPriority,
                      { backgroundColor: newTask.priority === priority ? getPriorityColor(priority) : '#f8f9fa' }
                    ]}
                    onPress={() => setNewTask({...newTask, priority})}
                  >
                    <Text style={[
                      styles.priorityButtonText,
                      newTask.priority === priority && styles.selectedPriorityText
                    ]}>
                      {priority}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
            
            <View style={styles.modalButtons}>
              <TouchableOpacity 
                style={styles.cancelButton} 
                onPress={() => setShowTaskForm(false)}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.createTaskButton} onPress={createTask}>
                <Text style={styles.createTaskButtonText}>Create Task</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
    marginBottom: 10,
    color: '#343a40',
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 40,
    color: '#6c757d',
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
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  companyList: {
    maxHeight: 100,
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
  credentialsInfo: {
    marginTop: 30,
    padding: 15,
    backgroundColor: '#e9ecef',
    borderRadius: 8,
  },
  credentialsTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#495057',
  },
  credentialsText: {
    fontSize: 12,
    color: '#6c757d',
    marginBottom: 2,
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
  headerButtons: {
    flexDirection: 'row',
    marginTop: 10,
    gap: 10,
  },
  createButton: {
    backgroundColor: '#28a745',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 4,
  },
  createButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  logoutButton: {
    backgroundColor: '#dc3545',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 4,
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
    marginBottom: 8,
    lineHeight: 20,
  },
  taskAssignee: {
    fontSize: 12,
    color: '#495057',
    fontStyle: 'italic',
    marginBottom: 8,
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
    paddingHorizontal: 8,
    paddingVertical: 4,
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
    fontSize: 10,
    fontWeight: 'bold',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 20,
    width: '90%',
    maxHeight: '80%',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
    color: '#343a40',
  },
  pickerContainer: {
    marginBottom: 20,
  },
  userList: {
    maxHeight: 120,
    borderWidth: 1,
    borderColor: '#ced4da',
    borderRadius: 8,
    backgroundColor: '#fff',
  },
  userItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  selectedUser: {
    backgroundColor: '#007bff',
  },
  userText: {
    fontSize: 14,
    color: '#495057',
  },
  selectedUserText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  priorityContainer: {
    marginBottom: 20,
  },
  priorityButtons: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
  },
  priorityButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#ced4da',
  },
  selectedPriority: {
    borderColor: 'transparent',
  },
  priorityButtonText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#495057',
  },
  selectedPriorityText: {
    color: '#fff',
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 10,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#6c757d',
    padding: 12,
    borderRadius: 4,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  createTaskButton: {
    flex: 1,
    backgroundColor: '#007bff',
    padding: 12,
    borderRadius: 4,
    alignItems: 'center',
  },
  createTaskButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
});
